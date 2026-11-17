"""Rate throttles for the screener's public endpoints.

Split out of `views.py` so `assistant.py` doesn't have to import it for one base class.
That import pulled the PolicyEngine registry, urgent-need calculation, serializers and
webhooks into the assistant module, and made any future `views -> assistant` reference a
startup import cycle.

Rates live in `DEFAULT_THROTTLE_RATES` (benefits/settings.py), keyed by `scope`.
"""

import hashlib
import logging
from collections.abc import Mapping
from typing import Any, Optional

from django.utils.crypto import salted_hmac
from rest_framework import throttling
from rest_framework.request import Request
from rest_framework.views import APIView

from integrations.services.communications.benji_sms_hash import InvalidPhoneNumber
from integrations.services.communications.benji_sms_hash import normalize as normalize_phone

logger = logging.getLogger(__name__)

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


def save_results_phone(data: Any) -> Optional[str]:
    """The E.164 number a Save My Results request asks to text, or None for no text.

    The one place the request's `phone` becomes a number, so the throttle keys on
    exactly the number `MessageViewSet` sends to. Parsing reuses the Benji SMS
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


class RateWindow(throttling.SimpleRateThrottle):
    """One scope's history for one key: is it full, and record one more.

    DRF's `SimpleRateThrottle.allow_request` checks and records in one step, and a
    view runs every throttle on every request. Stacking an hourly and a daily
    throttle therefore records an attempt against the daily limit even when the
    hourly one rejects it. This splits the two steps so a caller can look at several
    windows and only then decide whether to record.
    """

    def __init__(self, scope: str, ident: str) -> None:
        self.scope = scope
        super().__init__()
        self.key = self.cache_format % {"scope": scope, "ident": ident}
        self.now = self.timer()
        self.history = self.cache.get(self.key, [])
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

    def get_cache_key(self, request: Request, view: APIView) -> Optional[str]:
        return self.key

    @property
    def is_full(self) -> bool:
        return len(self.history) >= self.num_requests

    def record(self) -> None:
        self.throttle_success()


class SaveResultsRateThrottle(throttling.BaseThrottle):
    """Save My Results sends (the popup's email and text): per client IP and per phone.

    The endpoint makes MyFriendBen send to any address the caller supplies, behind
    the frontend's shared API token, which ships in the JS bundle. So being
    authenticated says nothing about who is calling, and every request is throttled.

    Four windows, with rates from `DEFAULT_THROTTLE_RATES`:

    - `message_ip`, `message_ip_day`: requests from one client IP. Budgeted far above
      any single household, because one public IP can be many: a navigator office
      or library, or a mobile carrier's NAT. The daily ceiling bounds a script.
    - `message_phone`, `message_phone_day`: texts sent to one number, from any IP.
      Fixing a mistyped number sends to a different number, so a household
      correcting a typo never spends this budget twice. Requests without a phone
      (email-only sends) have no phone windows.

    Two rules keep the limits from punishing the people they protect:

    1. **A rejected request costs nothing.** All windows are checked before any is
       recorded. Otherwise retrying while blocked for the hour would fill the day,
       and "please try again" would turn a one-hour block into a 24-hour one.
    2. **A number's budget counts texts sent, not attempts.** `allow_request` only
       checks the phone windows; the view calls `record_text` after Twilio accepts
       the message. A request for an unknown screen, or a send that fails, leaves
       the number's budget alone, so nobody can use up a number's day without
       texting it and an outage does not lock people out.

    The IP windows do count attempts, failed ones included: that is what bounds a
    script. Because a text is recorded after it is sent, simultaneous requests for
    one number can each pass the check; the overshoot is at most the number of
    requests in flight at once.

    Keys: the IP is hashed as the other throttles hash it. The phone is a keyed HMAC
    of the E.164 number rather than a plain hash, because a 10-digit number is small
    enough to brute-force from an unkeyed sha256. It uses Django's `salted_hmac`
    (SECRET_KEY) rather than Benji's `phone_hash`, whose BENJI_SMS_HASH_KEY may be
    unset where Save My Results already runs; the cache entry expires within a day,
    so it never needs to match a stored hash.
    """

    IP_SCOPES = ("message_ip", "message_ip_day")
    PHONE_SCOPES = ("message_phone", "message_phone_day")

    def __init__(self) -> None:
        self.blocked: list[RateWindow] = []

    def allow_request(self, request: Request, view: APIView) -> bool:
        ip_ident = self.ip_ident(request)
        phone_ident = self.phone_ident(request)
        ip_windows = self._windows(self.IP_SCOPES, ip_ident)
        phone_windows = self._windows(self.PHONE_SCOPES, phone_ident)

        self.blocked = [window for window in ip_windows + phone_windows if window.is_full]
        if self.blocked:
            # Which limit fired, and nothing about who hit it: the way to tell real
            # households being blocked from a script, and to tune the rates.
            logger.warning("Save My Results throttled by %s", ", ".join(window.scope for window in self.blocked))
            return False

        for window in ip_windows:
            window.record()
        return True

    def wait(self) -> Optional[float]:
        waits = [wait for wait in (window.wait() for window in self.blocked) if wait is not None]
        return max(waits, default=None)

    @classmethod
    def record_text(cls, phone: str) -> None:
        """Count one text sent to `phone`, the E.164 number from `save_results_phone`."""
        for window in cls._windows(cls.PHONE_SCOPES, cls._phone_hash(phone)):
            window.record()

    def ip_ident(self, request: Request) -> Optional[str]:
        ident = self.get_ident(request)
        return None if ident is None else hashlib.sha256(ident.encode()).hexdigest()

    def phone_ident(self, request: Request) -> Optional[str]:
        """The key for the number this request would text, or None for no text.

        An invalid phone has no key: the view refuses it with a 400 before sending.
        """
        try:
            phone = save_results_phone(request.data)
        except InvalidPhoneNumber:
            return None
        return None if phone is None else self._phone_hash(phone)

    @staticmethod
    def _phone_hash(phone: str) -> str:
        return salted_hmac(PHONE_KEY_SALT, phone, algorithm="sha256").hexdigest()

    @staticmethod
    def _windows(scopes: tuple[str, ...], ident: Optional[str]) -> list[RateWindow]:
        return [] if ident is None else [RateWindow(scope, ident) for scope in scopes]
