"""Rate throttles for the screener's public endpoints.

Split out of `views.py` so `assistant.py` doesn't have to import it for one base class.
That import pulled the PolicyEngine registry, urgent-need calculation, serializers and
webhooks into the assistant module, and made any future `views -> assistant` reference a
startup import cycle.

Rates live in `DEFAULT_THROTTLE_RATES` (benefits/settings.py), keyed by `scope`.
"""

import hashlib
import hmac

from django.conf import settings
from rest_framework import throttling


class HashedIPAnonRateThrottle(throttling.AnonRateThrottle):
    """AnonRateThrottle that keys on a hashed IP so raw IPs aren't stored."""

    def get_cache_key(self, request, view):
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

    Budgeted for a navigator office or library sending results for many households
    from one address, not for one household.
    """

    scope = "message_ip"


class MessageIPDailyRateThrottle(HashedIPAnonRateThrottle):
    """The daily ceiling behind `MessageIPRateThrottle`.

    The hourly rate alone would allow a script on one address roughly 24x its
    budget per day; this caps the total.
    """

    scope = "message_ip_day"


class MessagePhoneRateThrottle(throttling.SimpleRateThrottle):
    """Save My Results texts to one phone number, per hour.

    Fixing a mistyped number sends to a different number, so a household correcting
    a typo never spends this budget twice. What it bounds is repeated texts to the
    same number, from any IP. Requests without a phone (email-only sends) are not
    counted.

    The key is an HMAC of the number under SECRET_KEY rather than a plain hash: a
    10-digit number is small enough to brute-force from an unkeyed sha256.
    """

    scope = "message_phone"

    def get_cache_key(self, request, view):
        phone = request.data.get("phone") if hasattr(request.data, "get") else None
        if not isinstance(phone, str):
            return None
        ident = self.normalize_phone(phone)
        if not ident:
            return None
        hashed = hmac.new(settings.SECRET_KEY.encode(), ident.encode(), hashlib.sha256).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": hashed}

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """One key per US number however it was written.

        The popup sends `+1` and ten digits, but the endpoint is reachable without
        the popup, so "+1 (303) 555-0100", "3035550100" and "+13035550100" must not
        be three separate budgets. Keeping the last ten digits does that; a
        collision between two non-US inputs only makes the throttle stricter.
        """
        digits = "".join(c for c in phone if c.isdigit())
        return digits[-10:] if digits else phone.strip()


class MessagePhoneDailyRateThrottle(MessagePhoneRateThrottle):
    """The daily ceiling behind `MessagePhoneRateThrottle`."""

    scope = "message_phone_day"
