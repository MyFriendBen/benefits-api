"""The one place Benji SMS leaves benefits-api.

Benji over SMS ships dark (MFB-2433). Every Benji text goes through
``send_benji_sms``, which refuses unless all of these hold:

1. ``BENJI_SMS_OUTBOUND_ENABLED`` is set to a true value. Read fail-closed: missing,
   empty or anything unrecognised means off. This is the global kill switch, and the
   only gate on fixed replies that belong to no white label (stranger, expired, shared).
2. ``white_label.has_feature("benji_sms")``, when the send belongs to a screen.
3. ``settings.DEBUG`` is off, so local work never reaches Twilio.

Nothing else in the codebase should create a Twilio client for Benji. The Save My
Results text in ``message.py`` is a separate, older path and is not gated here.
"""

import logging
from typing import Optional

from decouple import config
from django.conf import settings
from twilio.rest import Client

from screener.models import WhiteLabel

logger = logging.getLogger(__name__)

FLAG = "benji_sms"
SWITCH = "BENJI_SMS_OUTBOUND_ENABLED"
_TRUE_VALUES = frozenset({"true", "1", "yes", "on"})


def outbound_enabled() -> bool:
    """The global kill switch. Missing or unrecognised means off.

    Read on every call rather than at import, so a test or a config change never
    sees a stale value.
    """
    raw = config(SWITCH, default="")
    return str(raw).strip().lower() in _TRUE_VALUES


def refusal_reason(white_label: Optional[WhiteLabel]) -> Optional[str]:
    """Why a Benji SMS may not be sent right now, or None if it may.

    ``white_label`` is None only for fixed replies that belong to no screen.
    """
    if not outbound_enabled():
        return "switch_off"
    if white_label is not None and not white_label.has_feature(FLAG):
        return "flag_off"
    if settings.DEBUG:
        return "debug"
    return None


def can_send(white_label: Optional[WhiteLabel]) -> bool:
    return refusal_reason(white_label) is None


def send_benji_sms(
    to: str,
    body: str,
    *,
    white_label: Optional[WhiteLabel],
    status_callback: Optional[str] = None,
) -> Optional[str]:
    """Send one Benji text if every gate allows it.

    ``white_label`` is keyword-only and has no default, so a caller has to say
    whether the send belongs to a screen. Pass None only for fixed replies with no
    white label; those are gated by the kill switch alone.

    Returns the Twilio message SID, or None when refused. A refusal is logged with
    its reason and the white label code, never the phone number or the body.
    """
    reason = refusal_reason(white_label)
    if reason is not None:
        logger.info(
            "Benji SMS send refused",
            extra={"reason": reason, "white_label": white_label.code if white_label else None},
        )
        return None

    kwargs = {
        "from_": str(config("TWILIO_PHONE_NUMBER", default="")),
        "to": to,
        "body": body,
    }
    if status_callback:
        kwargs["status_callback"] = status_callback

    message = _client().messages.create(**kwargs)
    return message.sid


def _client() -> Client:
    return Client(str(config("TWILIO_SID", default="")), str(config("TWILIO_TOKEN", default="")))
