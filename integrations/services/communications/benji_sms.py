"""The one place Benji SMS leaves benefits-api.

Benji over SMS ships dark (MFB-2433). Every Benji text goes through one of two
functions, and both refuse unless every gate that applies holds:

``send_screen_sms`` is for anything sent on behalf of a screen. Gates:
  1. ``BENJI_SMS_OUTBOUND_ENABLED`` is set to a true value. Read fail-closed: missing,
     empty or anything unrecognised means off. This is the global kill switch.
  2. A white label is given and ``white_label.has_feature("benji_sms")``. A missing
     white label refuses: it never means "skip the flag".
  3. ``settings.DEBUG`` is off, so local work never reaches Twilio.
  4. Twilio credentials and a sending number are configured.

``send_fixed_reply`` is for fixed replies that belong to no white label (stranger,
expired, shared). Same gates minus the flag.

Nothing else should send Benji texts or call ``twilio_client()``. The Save My Results
text in ``message.py`` is a separate path with its own client and is not gated here.

``delete_inbound_media`` is the one call here that sends nothing: it deletes the
pictures of an inbound MMS at Twilio (MFB-2439; proposal v3, decision 7). It is not
behind the kill switch or the flag, because turning Benji off must not leave people's
pictures at Twilio.

Failures raise one of two errors, both ``BenjiSmsError``, so a caller can tell
whether retrying is safe:

``BenjiSmsSendError``
    Not sent: Twilio rejected the request, or it never reached Twilio. Safe to retry.
``BenjiSmsDeliveryUnknown``
    The request may have reached Twilio (read timeout, connection dropped after
    sending). Retrying can text the person twice; record it and do not resend.

Nothing here logs or raises the phone number or the body: refusals log the reason
and white label code, and both errors carry only Twilio's status and error code or
the exception type, with the original chain suppressed.
"""

import logging
from typing import Optional

import requests
from django.conf import settings
from django.urls import NoReverseMatch, reverse
from twilio.base.exceptions import TwilioRestException

from screener.models import WhiteLabel

from .twilio_client import twilio_client

logger = logging.getLogger(__name__)

FLAG = "benji_sms"
SWITCH = "BENJI_SMS_OUTBOUND_ENABLED"
# The URL name of the status callback webhook (MFB-2441). Sends ask Twilio to report
# delivery to it once the route exists (`status_callback_url`).
STATUS_CALLBACK_URL_NAME = "benji-sms-status"
# `BenjiSmsMediaError.cause` when Twilio credentials are missing: a setup fault that a
# retry cannot fix.
MEDIA_NOT_CONFIGURED = "not_configured"
_TRUE_VALUES = frozenset({"true", "1", "yes", "on"})


class BenjiSmsError(Exception):
    """A Benji SMS send failed. Never carries the number or the body."""


class BenjiSmsSendError(BenjiSmsError):
    """Not sent. Carries Twilio's status and error code when Twilio answered."""

    def __init__(self, status: Optional[int], code: Optional[int]) -> None:
        self.status = status
        self.code = code
        super().__init__(f"Benji SMS not sent: status={status} code={code}")


class BenjiSmsMediaError(BenjiSmsError):
    """An inbound message's media could not be deleted at Twilio. Carries Twilio's
    status and error code when Twilio answered, or the exception type when it did not."""

    def __init__(self, status: Optional[int], code: Optional[int], cause: Optional[str] = None) -> None:
        self.status = status
        self.code = code
        self.cause = cause
        super().__init__(f"Benji SMS media not deleted: status={status} code={code} cause={cause}")

    def __reduce__(self) -> tuple:
        # Celery rebuilds a failed job's exception from its `args`, which here is the
        # one formatted message and does not fit `__init__`. Without this it falls back
        # to the nearest class it can rebuild, and the dead letter names `BenjiSmsError`.
        return (type(self), (self.status, self.code, self.cause))

    @property
    def retryable(self) -> bool:
        """Twilio never answered, is overloaded or is failing: worth another attempt.
        Any other answer (bad credentials, a refused request) will not change, and
        neither will missing credentials on our side."""
        if self.cause == MEDIA_NOT_CONFIGURED:
            return False
        return self.status is None or self.status == 429 or self.status >= 500


class BenjiSmsDeliveryUnknown(BenjiSmsError):
    """The request may have reached Twilio, so the text may have gone out. Do not resend."""

    def __init__(self, cause: str) -> None:
        self.cause = cause
        super().__init__(f"Benji SMS delivery unknown: {cause}")


def outbound_enabled() -> bool:
    """The global kill switch. Missing or unrecognised means off."""
    raw = getattr(settings, SWITCH, "")
    return str(raw).strip().lower() in _TRUE_VALUES


def _refusal_reason(white_label: Optional[WhiteLabel], *, screen_send: bool) -> Optional[str]:
    if not outbound_enabled():
        return "switch_off"
    if screen_send:
        if white_label is None:
            return "no_white_label"
        if not white_label.has_feature(FLAG):
            return "flag_off"
    if settings.DEBUG:
        return "debug"
    if not (settings.TWILIO_SID and settings.TWILIO_TOKEN and settings.TWILIO_PHONE_NUMBER):
        return "not_configured"
    return None


def can_send_for_screen(white_label: Optional[WhiteLabel]) -> bool:
    """Whether ``send_screen_sms`` would send for this white label right now.

    For callers that have work to do before sending (the on-ramp creates a binding
    and a conversation) and should skip it when the send would be refused anyway.
    """
    return _refusal_reason(white_label, screen_send=True) is None


def channel_enabled(white_label: Optional[WhiteLabel]) -> bool:
    """Whether Benji SMS is switched on for this white label: the kill switch and the flag.

    For deciding whether to start work that ends in a send, such as queueing a turn,
    which would pay for a model reply nobody can be sent. Unlike `can_send_for_screen`
    it ignores DEBUG and missing Twilio credentials, so local work still runs a turn
    end to end and stops only at the send.
    """
    return outbound_enabled() and white_label is not None and white_label.has_feature(FLAG)


def status_callback_url() -> Optional[str]:
    """Where Twilio should report a Benji text's delivery status, or None.

    None until the status callback route (MFB-2441) is registered under
    STATUS_CALLBACK_URL_NAME, so Twilio is never told to post to a URL that does not
    exist (each failed post would count as a webhook error). Once the route exists,
    every send that passes this gets delivery status with no further change.
    """
    try:
        path = reverse(STATUS_CALLBACK_URL_NAME)
    except NoReverseMatch:
        return None
    return str(settings.BACKEND_DOMAIN).rstrip("/") + path


def can_send_fixed_reply() -> bool:
    """Whether ``send_fixed_reply`` would send right now."""
    return _refusal_reason(None, screen_send=False) is None


def send_screen_sms(
    to: str,
    body: str,
    *,
    white_label: WhiteLabel,
    status_callback: Optional[str] = None,
) -> Optional[str]:
    """Send one Benji text on behalf of a screen, if every gate allows it.

    Returns the Twilio message SID, or None when refused. Passing None for
    ``white_label`` (say, from a nullable foreign key) refuses rather than skipping
    the flag. Raises ``BenjiSmsSendError`` if Twilio rejects the send.
    """
    return _send(to, body, white_label, screen_send=True, status_callback=status_callback)


def send_fixed_reply(to: str, body: str, *, status_callback: Optional[str] = None) -> Optional[str]:
    """Send a fixed reply that belongs to no white label, gated by the kill switch.

    Returns the Twilio message SID, or None when refused. Raises
    ``BenjiSmsSendError`` if Twilio rejects the send.
    """
    return _send(to, body, None, screen_send=False, status_callback=status_callback)


def _send(
    to: str,
    body: str,
    white_label: Optional[WhiteLabel],
    *,
    screen_send: bool,
    status_callback: Optional[str],
) -> Optional[str]:
    reason = _refusal_reason(white_label, screen_send=screen_send)
    if reason is not None:
        # In the message, not `extra`: no formatter here prints extras. WARNING because
        # this logger has no handler of its own and the root level drops INFO.
        logger.warning(
            "Benji SMS send refused: reason=%s white_label=%s",
            reason,
            white_label.code if white_label is not None else None,
        )
        return None

    kwargs = {"from_": settings.TWILIO_PHONE_NUMBER, "to": to, "body": body}
    if status_callback:
        kwargs["status_callback"] = status_callback

    try:
        message = twilio_client().messages.create(**kwargs)
    except ValueError as e:
        # The SDK decodes the 2xx body itself; an unreadable one (json.JSONDecodeError is
        # a ValueError) means Twilio answered and may have queued the text. The body is
        # never quoted.
        raise BenjiSmsDeliveryUnknown(type(e).__name__) from None
    except TwilioRestException as e:
        # Twilio's message can name the number ("The 'To' number +1... is not valid").
        # `from None` suppresses the chained original, which Sentry honours.
        raise BenjiSmsSendError(e.status, e.code) from None
    except requests.ConnectTimeout:
        # Never connected, so nothing was sent. Checked before ConnectionError,
        # which it subclasses.
        raise BenjiSmsSendError(None, None) from None
    except requests.RequestException as e:
        # Read timeout, or the connection dropped after the request went out: Twilio
        # may have queued the message.
        raise BenjiSmsDeliveryUnknown(type(e).__name__) from None
    if not message.sid:
        # Twilio answered 2xx but the SDK found no SID in the body: it may well have
        # queued the text, so this is not a refusal (which None means here).
        raise BenjiSmsDeliveryUnknown("no_sid")
    return message.sid


def delete_inbound_media(message_sid: str) -> int:
    """Delete every media file Twilio holds for one inbound message. Returns how many.

    Images are never stored (proposal v3, decision 7): Twilio keeps an inbound MMS's
    media until the account deletes it, so every inbound with media gets this, whoever
    sent it. Safe to repeat: media already gone, or a message that no longer exists,
    counts as done.

    Does nothing in DEBUG, where no real message exists. Raises `BenjiSmsMediaError`,
    which never carries the SID, when Twilio is not configured or refuses.
    """
    if settings.DEBUG:
        logger.warning("Benji SMS media deletion skipped: reason=debug")
        return 0
    if not (settings.TWILIO_SID and settings.TWILIO_TOKEN):
        raise BenjiSmsMediaError(None, None, MEDIA_NOT_CONFIGURED)

    deleted = 0
    try:
        for media in twilio_client().messages(message_sid).media.list():
            try:
                media.delete()
            except TwilioRestException as e:
                if e.status != 404:
                    raise
            deleted += 1
    except TwilioRestException as e:
        if e.status == 404:
            return deleted
        # Twilio's message can quote the request URL, which holds the SID.
        raise BenjiSmsMediaError(e.status, e.code) from None
    except requests.RequestException as e:
        raise BenjiSmsMediaError(None, None, type(e).__name__) from None
    return deleted
