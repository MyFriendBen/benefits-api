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

Nothing else in the codebase should create a Twilio client for Benji. The Save My
Results text in ``message.py`` is a separate, older path and is not gated here.

Nothing here logs or raises the phone number or the body: refusals log the reason
and white label code, and Twilio errors are re-raised as ``BenjiSmsSendError``
carrying only Twilio's status and error code.
"""

import logging
from typing import Optional

from decouple import config
from django.conf import settings
from twilio.base.exceptions import TwilioRestException

from screener.models import WhiteLabel

from .twilio_client import twilio_client

logger = logging.getLogger(__name__)

FLAG = "benji_sms"
SWITCH = "BENJI_SMS_OUTBOUND_ENABLED"
_TRUE_VALUES = frozenset({"true", "1", "yes", "on"})


class BenjiSmsSendError(Exception):
    """Twilio refused a send. Carries Twilio's status and error code, never the number."""

    def __init__(self, status: Optional[int], code: Optional[int]) -> None:
        self.status = status
        self.code = code
        super().__init__(f"Twilio refused a Benji SMS send: status={status} code={code}")


def outbound_enabled() -> bool:
    """The global kill switch. Missing or unrecognised means off.

    Read on every call rather than at import, so a test or a config change never
    sees a stale value.
    """
    raw = config(SWITCH, default="")
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
    except TwilioRestException as e:
        # Twilio's message can name the number ("The 'To' number +1... is not valid").
        # `from None` suppresses the chained original, which Sentry honours.
        raise BenjiSmsSendError(e.status, e.code) from None
    return message.sid
