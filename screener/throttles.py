"""Rate throttles for the screener's AllowAny proxy endpoints.

Split out of `views.py` so `assistant.py` doesn't have to import it for one base class.
That import pulled the PolicyEngine registry, urgent-need calculation, serializers and
webhooks into the assistant module, and made any future `views -> assistant` reference a
startup import cycle.

Rates live in `DEFAULT_THROTTLE_RATES` (benefits/settings.py), keyed by `scope`.
"""

import hashlib

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
