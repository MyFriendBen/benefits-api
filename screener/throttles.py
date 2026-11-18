"""Rate throttles for the screener's public endpoints.

Split out of `views.py` so `assistant.py` doesn't have to import it for one base class.
That import pulled the PolicyEngine registry, urgent-need calculation, serializers and
webhooks into the assistant module, and made any future `views -> assistant` reference a
startup import cycle.

Rates live in `DEFAULT_THROTTLE_RATES` (benefits/settings.py), keyed by `scope`.
"""

import hashlib
import logging
import time
from collections.abc import Mapping
from typing import Any, Optional

from django.core.cache import cache as default_cache
from django.utils.crypto import salted_hmac
from rest_framework import throttling
from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from benefits.throttle_config import parse_rate

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


class CacheUnavailable(Exception):
    """The cache didn't answer, so no limit can be checked."""


class RateWindow:
    """One limit (a scope's rate) for one key, counted atomically in the cache.

    A sliding-window counter: one integer per fixed window (an hour, a day), and a
    request's count is this window's plus the previous window's, weighted by how
    much of it still overlaps the last `duration` seconds. It assumes the previous
    window's requests were spread evenly, so it can differ from an exact count of the
    last `duration` seconds: a burst just before a boundary stays counted a little
    past `duration`, and in the worst timing (a full window's worth at the very end
    of one window, then another spread across the next) a span of `duration` can
    hold up to twice the limit. That bound is what the limits guarantee.

    It isn't a `SimpleRateThrottle` because DRF keeps a timestamp list that it reads,
    appends to and writes back, so two workers recording against one key at once
    each write a list holding only their own entry, and one record is lost. Here
    every change is a single `incr` on the cache (Redis INCRBY), so concurrent
    requests cannot overwrite each other: `reserve` takes a slot and sees the count
    including everyone else's, and `release` gives one back.
    """

    cache = default_cache
    timer = staticmethod(time.time)
    THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    def __init__(self, scope: str, ident: str) -> None:
        self.scope = scope
        self.limit, self.duration = parse_rate(self.THROTTLE_RATES[scope])
        now = self.timer()
        window = int(now // self.duration)
        self.key = f"throttle_{scope}_{ident}_{window}"
        self.previous_key = f"throttle_{scope}_{ident}_{window - 1}"
        self.elapsed = now - window * self.duration
        # What a refused `reserve` saw, for `wait`.
        self.current = 0
        self.previous = 0

    def reserve(self) -> bool:
        """Take a slot if the limit allows it; leave the count unchanged if not.

        Raises `CacheUnavailable` if the cache doesn't answer.
        """
        count = self._add(1)
        self.previous = self.cache.get(self.previous_key) or 0
        weight = self.previous * (self.duration - self.elapsed) / self.duration
        if count + weight <= self.limit:
            return True
        if not self.release():
            raise CacheUnavailable()
        self.current = count - 1
        return False

    def release(self) -> bool:
        """Give back a slot taken by `reserve`; False if the cache didn't answer.

        Only decrements a counter that still exists. If it is gone (a Redis restart
        or an eviction since `reserve`), there is nothing to give back, and
        recreating it would leave it at -1: one slot more than the limit.
        """
        try:
            return self.cache.incr(self.key, -1) is not None
        except ValueError:
            return True

    def wait(self) -> float:
        """Seconds until one more request fits, if nothing else is counted meanwhile."""
        remaining = self.duration - self.elapsed
        if self.limit < 1:
            return remaining
        room = self.limit - 1 - self.current
        if room >= 0:
            # It fits in this window once enough of the previous one has slid out.
            return max(0.0, remaining - self.duration * room / self.previous) if self.previous else 0.0
        # This window alone is full: wait for it to become the previous window,
        # then for enough of it to slide out.
        return remaining + self.duration * (1 - (self.limit - 1) / self.current)

    def _add(self, delta: int) -> int:
        # Kept through the next window too, where it is the previous window. `add`
        # answers False when the counter already exists and None when the cache
        # didn't answer at all; stop there rather than wait out a second timeout.
        if self.cache.add(self.key, 0, timeout=2 * self.duration) is None:
            raise CacheUnavailable()
        try:
            count = self.cache.incr(self.key, delta)
        except ValueError:
            # The key was evicted between add and incr.
            count = None
        if count is None:
            raise CacheUnavailable()
        return count


class SaveResultsRateThrottle(throttling.BaseThrottle):
    """Save My Results sends (the popup's email and text): per client IP and per phone.

    The endpoint makes MyFriendBen send to any address the caller supplies, behind
    the frontend's shared API token, which ships in the JS bundle. So being
    authenticated says nothing about who is calling, and every request is throttled.

    Four limits, with rates from `DEFAULT_THROTTLE_RATES`:

    - `message_ip`, `message_ip_day`: requests from one client IP. Budgeted far above
      any single household, because one public IP can be many: a navigator office
      or library, or a mobile carrier's NAT. The daily ceiling bounds a script.
    - `message_phone`, `message_phone_day`: texts sent to one number, from any IP.
      Fixing a mistyped number sends to a different number, so a household
      correcting a typo never spends this budget twice. Requests without a phone
      (email-only sends) have no phone limits.

    Only POST is throttled: it is the only method that sends anything, and a GET or
    OPTIONS from a shared address shouldn't use up that address's budget.

    Every limit takes its slot before the request goes on (see `RateWindow`), so
    concurrent requests are counted exactly. If the cache doesn't answer, the request
    is allowed at the first unanswered call, keeping whatever slots it had taken,
    rather than waiting out a timeout on each of the remaining ones: the throttle fails open, quickly, instead of blocking
    everyone or holding a worker. Two rules keep the limits from punishing the people
    they protect:

    1. **A rejected request costs nothing.** If any limit refuses the request, every
       slot it took is given back. Otherwise retrying while blocked for the hour
       would fill the day, and "please try again" would turn a one-hour block into
       a 24-hour one.
    2. **A number's budget counts texts sent, not attempts.** The phone slots are
       held while the request runs and given back by `release_text` unless Twilio
       accepted the text. A request for an unknown screen, or a send Twilio
       refuses, leaves the number's budget alone, so nobody can use up a number's
       day without texting it and an outage does not lock people out.

    The IP limits do count attempts, failed ones included: that is what bounds a
    script.

    Keys: the IP is hashed as the other throttles hash it. The phone is a keyed HMAC
    of the E.164 number rather than a plain hash, because a 10-digit number is small
    enough to brute-force from an unkeyed sha256. It uses Django's `salted_hmac`
    (SECRET_KEY) rather than Benji's `phone_hash`, whose BENJI_SMS_HASH_KEY may be
    unset where Save My Results already runs; the counters expire within two days,
    so they never need to match a stored hash.
    """

    IP_SCOPES = ("message_ip", "message_ip_day")
    PHONE_SCOPES = ("message_phone", "message_phone_day")
    # Where `allow_request` leaves the phone slots it took, for `release_text`.
    PHONE_SLOTS = "save_results_phone_slots"

    def __init__(self) -> None:
        self.blocked: list[RateWindow] = []

    def allow_request(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return True
        ip_windows = self._windows(self.IP_SCOPES, self.ip_ident(request))
        phone_windows = self._windows(self.PHONE_SCOPES, self.phone_ident(request))

        reserved = []
        try:
            for window in ip_windows + phone_windows:
                if window.reserve():
                    reserved.append(window)
                else:
                    self.blocked.append(window)
        except CacheUnavailable:
            # Allowed, with no further cache calls. Slots already taken stay taken:
            # the request goes on to send, so they are what happened, and giving
            # them back would mean more calls to a cache that just failed.
            logger.warning("Save My Results throttle skipped: the cache did not answer")
            self.blocked = []
            setattr(request, self.PHONE_SLOTS, [window for window in reserved if window in phone_windows])
            return True

        if self.blocked:
            self._release(reserved)
            # Which limit fired, and nothing about who hit it: the way to tell real
            # households being blocked from a script, and to tune the rates.
            logger.warning("Save My Results throttled by %s", ", ".join(window.scope for window in self.blocked))
            return False

        setattr(request, self.PHONE_SLOTS, phone_windows)
        return True

    def wait(self) -> Optional[float]:
        return max((window.wait() for window in self.blocked), default=None)

    @classmethod
    def release_text(cls, request: Request) -> None:
        """Give back the phone slots this request took: its text was not sent."""
        cls._release(getattr(request, cls.PHONE_SLOTS, []))
        setattr(request, cls.PHONE_SLOTS, [])

    @staticmethod
    def _release(windows: list[RateWindow]) -> None:
        """Give slots back, stopping at the first call the cache doesn't answer."""
        for window in windows:
            if not window.release():
                break

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
        return None if phone is None else salted_hmac(PHONE_KEY_SALT, phone, algorithm="sha256").hexdigest()

    @staticmethod
    def _windows(scopes: tuple[str, ...], ident: Optional[str]) -> list[RateWindow]:
        return [] if ident is None else [RateWindow(scope, ident) for scope in scopes]
