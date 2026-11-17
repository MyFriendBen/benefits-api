"""Rate throttles for the screener's public endpoints.

Split out of `views.py` so `assistant.py` doesn't have to import it for one base class.
That import pulled the PolicyEngine registry, urgent-need calculation, serializers and
webhooks into the assistant module, and made any future `views -> assistant` reference a
startup import cycle.

Rates live in `DEFAULT_THROTTLE_RATES` (benefits/settings.py), keyed by `scope`.
"""

import hashlib
from collections.abc import Mapping
from typing import Any, Optional

from django.utils.crypto import salted_hmac
from rest_framework import throttling
from rest_framework.request import Request
from rest_framework.views import APIView

from integrations.services.communications.benji_sms_hash import InvalidPhoneNumber
from integrations.services.communications.benji_sms_hash import normalize as normalize_phone

PHONE_KEY_SALT = "screener.throttles.message_phone"


class HashedIPAnonRateThrottle(throttling.AnonRateThrottle):
    """AnonRateThrottle that keys on a hashed IP so raw IPs aren't stored."""

    def get_cache_key(self, request: Request, view: APIView) -> Optional[str]:
        ident = self.get_ident(request)
        if ident is None:
            return None
        hashed = hashlib.sha256(ident.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": hashed}


class NPSRateThrottle(HashedIPAnonRateThrottle):
    scope = "nps"


class PlacesRateThrottle(HashedIPAnonRateThrottle):
    scope = "places"


class RemRateThrottle(HashedIPAnonRateThrottle):
    scope = "rem"


class AssistantStartRateThrottle(HashedIPAnonRateThrottle):
    """Opening (or resuming) a Benbot conversation.

    AllowAny, proxies to a paid LLM, and persists context in ai-service — so it isn't
    only a cost concern. Same shape as the REM and Places proxies, which are throttled
    for the same reason.
    """

    scope = "assistant_start"


class AssistantMessageRateThrottle(HashedIPAnonRateThrottle):
    """Sending a Benbot message. Holds a worker for up to AI_SERVICE_TIMEOUT (60s)."""

    scope = "assistant_message"


class AssistantRatingRateThrottle(HashedIPAnonRateThrottle):
    """Rating a Benbot reply (thumbs up/down).

    Cheaper than any of the above — one indexed UPDATE, no context assembly and no
    LLM — but the most clickable: the buttons sit on every assistant bubble, and
    re-clicking is how a rating is changed or cleared, so a single user legitimately
    spends several of these on one reply while making up their mind. Budgeted well
    above that and still far below what a script would want.
    """

    scope = "assistant_rating"


class AssistantHistoryRateThrottle(HashedIPAnonRateThrottle):
    """Reading a Benbot transcript back.

    Separate from `assistant_start` because it is a much cheaper call — no context
    assembly, no LLM, one indexed lookup in ai-service — and a much more frequent one:
    the widget auto-opens on nearly every results page, and a page reload repeats it.
    Sharing the start budget would let ordinary browsing exhaust the ability to open a
    conversation at all.
    """

    scope = "assistant_history"


class MessageIPRateThrottle(HashedIPAnonRateThrottle):
    """Save My Results sends (the popup's email and text), per client IP, per hour.

    The endpoint sits behind the frontend's shared API token, which ships in the JS
    bundle, so being authenticated says nothing about who is calling. The IP key
    applies to authenticated requests too: `HashedIPAnonRateThrottle` replaces
    `AnonRateThrottle.get_cache_key`, which is what would exempt them.

    Budgeted far above any single household, because one public IP can be many:
    a navigator office or library sending for the people it serves, or a mobile
    carrier's NAT putting unrelated phones behind one address. The daily ceiling is
    what bounds a script.
    """

    scope = "message_ip"


class MessageIPDailyRateThrottle(HashedIPAnonRateThrottle):
    """The daily ceiling behind `MessageIPRateThrottle`.

    The hourly rate alone would let a script on one address send 24x that rate per
    day; this caps the total.
    """

    scope = "message_ip_day"


def save_results_phone(data: Any) -> Optional[str]:
    """The E.164 number a Save My Results request asks to text, or None for no text.

    The one place the request's `phone` becomes a number, so the phone throttles key
    on exactly the number `MessageViewSet` sends to. Parsing reuses the Benji SMS
    normalizer, which reads numbers without a `+` as US numbers: "+1 (303) 555-0100",
    "3035550100" and "+13035550100" are one number to the throttle and to Twilio.

    Raises `InvalidPhoneNumber` for a `phone` that is present but not a phone number,
    including a non-string such as a JSON number; the view refuses those with a 400
    rather than handing them to Twilio.
    """
    phone = data.get("phone") if isinstance(data, Mapping) else None
    if phone is None:
        return None
    if not isinstance(phone, str):
        raise InvalidPhoneNumber()
    return normalize_phone(phone)


class MessagePhoneRateThrottle(throttling.SimpleRateThrottle):
    """Save My Results texts to one phone number, per hour.

    Fixing a mistyped number sends to a different number, so a household correcting
    a typo never spends this budget twice. What it bounds is repeated texts to the
    same number, from any IP. Requests without a phone (email-only sends) are not
    counted, and neither are invalid ones, which the view refuses without sending.

    The key is a keyed HMAC of the E.164 number rather than a plain hash: a 10-digit
    number is small enough to brute-force from an unkeyed sha256. It uses Django's
    `salted_hmac` (SECRET_KEY) rather than Benji's `phone_hash`, whose
    BENJI_SMS_HASH_KEY may be unset where Save My Results already runs; the cache
    entry expires within a day, so it never needs to match a stored hash.
    """

    scope = "message_phone"

    def get_cache_key(self, request: Request, view: APIView) -> Optional[str]:
        try:
            phone = save_results_phone(request.data)
        except InvalidPhoneNumber:
            return None
        if phone is None:
            return None
        hashed = salted_hmac(PHONE_KEY_SALT, phone, algorithm="sha256").hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": hashed}


class MessagePhoneDailyRateThrottle(MessagePhoneRateThrottle):
    """The daily ceiling behind `MessagePhoneRateThrottle`."""

    scope = "message_phone_day"
