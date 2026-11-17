"""Throttles on the Save My Results message endpoint (MFB-2437).

The endpoint makes MyFriendBen email or text any address the caller supplies, behind
a token that ships in the frontend bundle. "It's configured" isn't enough here:
these tests assert each throttle engages, returns 429, and stops the send.

Throttle history is cache-backed, so the cache is pinned to a per-process LocMemCache
(see `benefits/tests/cache_override.py`) and cleared around every test.
"""

import hashlib
import json
from typing import Optional
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authentication.models import User
from benefits.tests.cache_override import LOCAL_CACHE
from screener.models import Screen, WhiteLabel
from screener.throttles import (
    MessageIPDailyRateThrottle,
    MessageIPRateThrottle,
    MessagePhoneDailyRateThrottle,
    MessagePhoneRateThrottle,
)

URL = "/api/messages/"
PHONE = "+13035550100"


def _limit(scope: str) -> int:
    return int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope].split("/")[0])


def _rates_with(**overrides: str) -> dict[str, str]:
    """The configured rates with some lifted, to reach a daily ceiling in a test.

    Patched as a whole dict because the daily phone throttle subclasses the hourly
    one and reads the same `THROTTLE_RATES` attribute.
    """
    return {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], **overrides}


@override_settings(CACHES=LOCAL_CACHE)
@mock.patch("screener.views.MessageUser")
class MessageThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(white_label=white_label, zipcode="78701", household_size=1, completed=True)

        # The frontend posts with a token user; DjangoModelPermissions maps POST to
        # screener.add_message. Authenticated callers are throttled all the same.
        user = User.objects.create_user(email_or_cell="frontend@example.com", password="password")
        user.user_permissions.add(Permission.objects.get(codename="add_message", content_type__app_label="screener"))
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def _post(self, ip: str = "203.0.113.1", forwarded_for: Optional[str] = None, **payload) -> int:
        body = {"screen": str(self.screen.uuid), "type": "textScreen", **payload}
        extra = {"REMOTE_ADDR": ip}
        if forwarded_for is not None:
            extra["HTTP_X_FORWARDED_FOR"] = forwarded_for
        return self.client.post(URL, body, format="json", **extra).status_code

    # Per IP

    def test_ip_throttle_returns_429_after_the_hourly_limit(self, message_user):
        limit = _limit("message_ip")

        # A different address every time, so only the IP budget is in play.
        statuses = [self._post(email=f"person{i}@example.com") for i in range(limit + 1)]

        self.assertNotIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses[:limit])
        self.assertEqual(statuses[-1], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_ip_throttle_counts_texts_to_different_numbers(self, message_user):
        """The case the ticket is about: one caller, many numbers."""
        limit = _limit("message_ip")

        statuses = [self._post(phone=f"+1303555{i:04d}") for i in range(limit + 1)]

        self.assertEqual(statuses[-1], status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(message_user.return_value.text.call_count, limit)

    def test_ip_throttle_is_per_ip(self, message_user):
        limit = _limit("message_ip")
        for i in range(limit):
            self._post(email=f"person{i}@example.com")

        self.assertEqual(self._post(ip="203.0.113.1", email="x@example.com"), status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(self._post(ip="203.0.113.2", email="x@example.com"), status.HTTP_201_CREATED)

    def test_a_spoofed_forwarded_for_does_not_buy_a_fresh_ip_budget(self, message_user):
        """Heroku's router appends the IP it saw to X-Forwarded-For, after whatever the
        client sent. Only that last entry counts, so rotating the rest changes nothing."""
        limit = _limit("message_ip")

        statuses = [
            self._post(forwarded_for=f"10.0.{i // 256}.{i % 256}, 203.0.113.9", email=f"person{i}@example.com")
            for i in range(limit + 1)
        ]

        self.assertNotIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses[:limit])
        self.assertEqual(statuses[-1], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_ip_daily_ceiling_holds_when_the_hourly_rate_would_allow_more(self, message_user):
        limit = _limit("message_ip_day")

        with mock.patch.object(MessageIPRateThrottle, "THROTTLE_RATES", _rates_with(message_ip="100000/hour")):
            statuses = [self._post(email=f"person{i}@example.com") for i in range(limit + 1)]

        self.assertNotIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses[:limit])
        self.assertEqual(statuses[-1], status.HTTP_429_TOO_MANY_REQUESTS)

    # Per phone

    def test_phone_throttle_returns_429_after_the_hourly_limit_from_any_ip(self, message_user):
        limit = _limit("message_phone")

        # A different IP every time, so only the phone budget is in play.
        statuses = [self._post(ip=f"198.51.100.{i}", phone=PHONE) for i in range(limit + 1)]

        self.assertNotIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses[:limit])
        self.assertEqual(statuses[-1], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_phone_daily_ceiling_holds_when_the_hourly_rate_would_allow_more(self, message_user):
        limit = _limit("message_phone_day")

        with mock.patch.object(MessagePhoneRateThrottle, "THROTTLE_RATES", _rates_with(message_phone="100000/hour")):
            statuses = [self._post(ip=f"198.51.100.{i}", phone=PHONE) for i in range(limit + 1)]

        self.assertNotIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses[:limit])
        self.assertEqual(statuses[-1], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_a_typo_fix_is_a_different_budget(self, message_user):
        """A household retrying a mistyped number never hits the phone throttle."""
        limit = _limit("message_phone")
        for i in range(limit):
            self._post(ip=f"198.51.100.{i}", phone=PHONE)

        self.assertEqual(self._post(ip="198.51.100.200", phone="+13035550101"), status.HTTP_201_CREATED)

    def test_sends_the_number_the_throttle_counted(self, message_user):
        """The throttle keys on the E.164 form, so that is the form sent to Twilio."""
        self.assertEqual(self._post(phone="(303) 555-0100"), status.HTTP_201_CREATED)

        message_user.return_value.text.assert_called_once_with(PHONE, send_tests=True)

    def test_a_non_string_phone_is_refused_and_not_sent(self, message_user):
        """A JSON number skips the phone throttle, so it must not reach Twilio either."""
        self.assertEqual(self._post(phone=13035550100), status.HTTP_400_BAD_REQUEST)

        message_user.assert_not_called()

    def test_an_invalid_phone_is_refused_and_not_sent(self, message_user):
        # A 7-digit number has no area code; every such number would share one key.
        self.assertEqual(self._post(phone="555-0100"), status.HTTP_400_BAD_REQUEST)

        message_user.assert_not_called()

    def test_email_only_sends_do_not_spend_a_phone_budget(self, message_user):
        for i in range(_limit("message_phone_day") + 1):
            self._post(ip=f"198.51.100.{i}", email="same@example.com")

        self.assertEqual(self._post(ip="198.51.100.200", phone=PHONE), status.HTTP_201_CREATED)

    def test_throttled_request_sends_nothing(self, message_user):
        limit = _limit("message_phone")
        for i in range(limit):
            self._post(ip=f"198.51.100.{i}", phone=PHONE)
        message_user.reset_mock()

        self.assertEqual(self._post(ip="198.51.100.200", phone=PHONE), status.HTTP_429_TOO_MANY_REQUESTS)
        message_user.assert_not_called()

    def test_the_normal_flow_still_sends(self, message_user):
        self.assertEqual(self._post(phone=PHONE, language="es"), status.HTTP_201_CREATED)

        message_user.assert_called_once_with(self.screen, "es")
        message_user.return_value.text.assert_called_once_with(PHONE, send_tests=True)

    # Request body

    def test_a_json_body_is_read_whatever_the_declared_content_type(self, message_user):
        """Before the throttle, the view parsed the raw body as JSON regardless of
        Content-Type. Going through DRF's parsing must not narrow that."""
        body = json.dumps({"screen": str(self.screen.uuid), "phone": PHONE})

        response = self.client.post(URL, body, content_type="text/plain", REMOTE_ADDR="203.0.113.1")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message_user.return_value.text.assert_called_once_with(PHONE, send_tests=True)

    def test_a_body_that_is_not_an_object_is_a_400(self, message_user):
        response = self.client.post(URL, [PHONE], format="json", REMOTE_ADDR="203.0.113.1")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        message_user.assert_not_called()


class MessagePhoneCacheKeyTests(SimpleTestCase):
    """The phone number never reaches the cache in a recoverable form."""

    def _key(self, data) -> Optional[str]:
        request = mock.Mock(data=data)
        return MessagePhoneRateThrottle().get_cache_key(request, view=None)

    def test_key_does_not_contain_the_number(self):
        key = self._key({"phone": PHONE})

        self.assertNotIn("3035550100", key)

    def test_key_is_keyed_not_a_plain_hash(self):
        """An unkeyed sha256 of a 10-digit number can be reversed by enumeration."""
        key = self._key({"phone": PHONE})

        self.assertNotIn(hashlib.sha256(b"3035550100").hexdigest(), key)
        self.assertNotIn(hashlib.sha256(PHONE.encode()).hexdigest(), key)

    def test_formatting_variants_share_one_key(self):
        """The endpoint is reachable without the popup, so reformatting the same
        number must not buy a fresh budget."""
        variants = ["+13035550100", "3035550100", "+1 (303) 555-0100", "303-555-0100", "13035550100"]

        self.assertEqual({self._key({"phone": phone}) for phone in variants}, {self._key({"phone": PHONE})})

    def test_no_phone_is_not_throttled(self):
        self.assertIsNone(self._key({"email": "a@example.com"}))
        self.assertIsNone(self._key({"phone": None}))
        self.assertIsNone(self._key([PHONE]))

    def test_an_invalid_phone_is_not_counted(self):
        """The view refuses these with a 400 before sending anything, so there is
        no send to budget."""
        self.assertIsNone(self._key({"phone": ""}))
        self.assertIsNone(self._key({"phone": "555-0100"}))
        self.assertIsNone(self._key({"phone": 3035550100}))

    def test_hourly_and_daily_keys_are_separate(self):
        request = mock.Mock(data={"phone": PHONE})
        hourly = MessagePhoneRateThrottle().get_cache_key(request, view=None)
        daily = MessagePhoneDailyRateThrottle().get_cache_key(request, view=None)

        self.assertNotEqual(hourly, daily)

    def test_every_scope_has_a_rate(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        for throttle in (
            MessageIPRateThrottle,
            MessageIPDailyRateThrottle,
            MessagePhoneRateThrottle,
            MessagePhoneDailyRateThrottle,
        ):
            self.assertIn(throttle.scope, rates)
