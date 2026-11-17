"""Throttles on the Save My Results message endpoint (MFB-2437).

The endpoint makes MyFriendBen email or text any address the caller supplies, behind
a token that ships in the frontend bundle. "It's configured" isn't enough here:
these tests assert the throttle engages, returns 429 and stops the send, and that
it does not punish the households it protects (a rejected request costs nothing; a
number's budget counts texts sent, not attempts).

Throttle history is cache-backed, so the cache is pinned to a per-process LocMemCache
(see `benefits/tests/cache_override.py`) and cleared around every test. The rates
are pinned too: production rates come from the environment, and small ones keep
each test to a handful of requests.
"""

import hashlib
import json
import time
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
from benefits.throttle_config import is_valid_rate
from screener.models import Screen, WhiteLabel
from screener.throttles import RateWindow, SaveResultsRateThrottle

URL = "/api/messages/"
PHONE = "+13035550100"
OTHER_PHONE = "+13035550101"
UNKNOWN_SCREEN = "00000000-0000-0000-0000-000000000000"

RATES = {
    "message_ip": "4/hour",
    "message_ip_day": "6/day",
    "message_phone": "2/hour",
    "message_phone_day": "3/day",
}
IP_HOUR, IP_DAY, PHONE_HOUR, PHONE_DAY = (int(rate.split("/")[0]) for rate in RATES.values())

OK = status.HTTP_201_CREATED
THROTTLED = status.HTTP_429_TOO_MANY_REQUESTS
JUST_OVER_AN_HOUR = 61 * 60


@override_settings(CACHES=LOCAL_CACHE)
@mock.patch("screener.views.MessageUser")
class MessageThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

        rates = mock.patch.object(RateWindow, "THROTTLE_RATES", RATES)
        rates.start()
        self.addCleanup(rates.stop)

        # A clock the tests can move, so a daily ceiling can be reached without a
        # day's worth of requests.
        self.now = time.time()
        clock = mock.patch.object(RateWindow, "timer", staticmethod(lambda: self.now))
        clock.start()
        self.addCleanup(clock.stop)

        white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(white_label=white_label, zipcode="78701", household_size=1, completed=True)

        # The frontend posts with a token user; DjangoModelPermissions maps POST to
        # screener.add_message. Authenticated callers are throttled all the same.
        user = User.objects.create_user(email_or_cell="frontend@example.com", password="password")
        user.user_permissions.add(Permission.objects.get(codename="add_message", content_type__app_label="screener"))
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        # A failing send is a 500 response here, as in production, not a raised error.
        self.client.raise_request_exception = False

    def _post(
        self, ip: str = "203.0.113.1", forwarded_for: Optional[str] = None, screen: Optional[str] = None, **payload
    ) -> int:
        body = {"screen": screen or str(self.screen.uuid), "type": "textScreen", **payload}
        extra = {"REMOTE_ADDR": ip}
        if forwarded_for is not None:
            extra["HTTP_X_FORWARDED_FOR"] = forwarded_for
        return self.client.post(URL, body, format="json", **extra).status_code

    def _emails(self, count: int, ip: str = "203.0.113.1") -> list[int]:
        """`count` sends from one IP, each to a different address: only the IP
        budget is in play."""
        return [self._post(ip=ip, email=f"person{i}@example.com") for i in range(count)]

    def _texts(self, count: int, phone: str = PHONE, **payload) -> list[int]:
        """`count` texts to one number, each from a different IP: only the phone
        budget is in play."""
        return [self._post(ip=f"198.51.100.{i}", phone=phone, **payload) for i in range(count)]

    def _wait(self, seconds: int) -> None:
        self.now += seconds

    # Per IP

    def test_ip_throttle_returns_429_after_the_hourly_limit(self, message_user):
        self.assertEqual(self._emails(IP_HOUR + 1), [OK] * IP_HOUR + [THROTTLED])

    def test_ip_throttle_counts_texts_to_different_numbers(self, message_user):
        """The case the ticket is about: one caller, many numbers."""
        statuses = [self._post(phone=f"+1303555{i:04d}") for i in range(IP_HOUR + 1)]

        self.assertEqual(statuses[-1], THROTTLED)
        self.assertEqual(message_user.return_value.text.call_count, IP_HOUR)

    def test_ip_throttle_is_per_ip(self, message_user):
        self._emails(IP_HOUR)

        self.assertEqual(self._post(ip="203.0.113.1", email="x@example.com"), THROTTLED)
        self.assertEqual(self._post(ip="203.0.113.2", email="x@example.com"), OK)

    def test_a_spoofed_forwarded_for_does_not_buy_a_fresh_ip_budget(self, message_user):
        """Heroku's router appends the IP it saw to X-Forwarded-For, after whatever the
        client sent. Only that last entry counts, so rotating the rest changes nothing."""
        statuses = [
            self._post(forwarded_for=f"10.0.0.{i}, 203.0.113.9", email=f"person{i}@example.com")
            for i in range(IP_HOUR + 1)
        ]

        self.assertEqual(statuses, [OK] * IP_HOUR + [THROTTLED])

    def test_ip_daily_ceiling_holds_once_the_hour_has_passed(self, message_user):
        self.assertEqual(self._emails(IP_HOUR), [OK] * IP_HOUR)
        self._wait(JUST_OVER_AN_HOUR)
        self.assertEqual(self._emails(IP_DAY - IP_HOUR), [OK] * (IP_DAY - IP_HOUR))
        self._wait(JUST_OVER_AN_HOUR)

        self.assertEqual(self._post(email="late@example.com"), THROTTLED)

    def test_requests_rejected_for_the_hour_do_not_spend_the_ip_day(self, message_user):
        """Otherwise one misbehaving client on a shared address could use up everyone
        else's day in a single burst."""
        self._emails(IP_HOUR)
        self.assertEqual(self._emails(IP_DAY * 2), [THROTTLED] * (IP_DAY * 2))
        self._wait(JUST_OVER_AN_HOUR)

        self.assertEqual(self._post(email="next-hour@example.com"), OK)

    def test_failed_sends_still_count_against_the_ip(self, message_user):
        """The IP budget counts attempts, which is what bounds a script."""
        message_user.return_value.email.side_effect = RuntimeError("SendGrid is down")

        statuses = self._emails(IP_HOUR + 1)

        self.assertEqual(statuses, [status.HTTP_500_INTERNAL_SERVER_ERROR] * IP_HOUR + [THROTTLED])

    def test_a_throttled_response_says_when_to_retry(self, message_user):
        self._emails(IP_HOUR)

        response = self.client.post(
            URL, {"screen": str(self.screen.uuid), "email": "x@example.com"}, format="json", REMOTE_ADDR="203.0.113.1"
        )

        self.assertEqual(response.status_code, THROTTLED)
        self.assertGreater(int(response["Retry-After"]), 0)

    # Per phone

    def test_phone_throttle_returns_429_after_the_hourly_limit_from_any_ip(self, message_user):
        self.assertEqual(self._texts(PHONE_HOUR + 1), [OK] * PHONE_HOUR + [THROTTLED])

    def test_phone_daily_ceiling_holds_once_the_hour_has_passed(self, message_user):
        self.assertEqual(self._texts(PHONE_HOUR), [OK] * PHONE_HOUR)
        self._wait(JUST_OVER_AN_HOUR)
        self.assertEqual(self._texts(PHONE_DAY - PHONE_HOUR), [OK] * (PHONE_DAY - PHONE_HOUR))
        self._wait(JUST_OVER_AN_HOUR)

        self.assertEqual(self._texts(1), [THROTTLED])

    def test_retrying_while_blocked_for_the_hour_does_not_spend_the_day(self, message_user):
        """The popup says "please try again". Doing so must not turn a one-hour
        block into a 24-hour one."""
        self._texts(PHONE_HOUR)
        self.assertEqual(self._texts(PHONE_DAY * 2), [THROTTLED] * (PHONE_DAY * 2))
        self._wait(JUST_OVER_AN_HOUR)

        self.assertEqual(self._texts(1), [OK])

    def test_a_request_rejected_for_the_phone_does_not_spend_the_ip_budget(self, message_user):
        ip = "203.0.113.50"
        for _ in range(PHONE_HOUR):
            self.assertEqual(self._post(ip=ip, phone=PHONE), OK)
        for _ in range(IP_HOUR * 2):
            self.assertEqual(self._post(ip=ip, phone=PHONE), THROTTLED)

        self.assertEqual(self._emails(IP_HOUR - PHONE_HOUR, ip=ip), [OK] * (IP_HOUR - PHONE_HOUR))

    def test_a_failed_send_does_not_spend_the_phone_budget(self, message_user):
        """A Twilio outage, or a number Twilio rejects, must not lock the person out
        once sending works again."""
        message_user.return_value.text.side_effect = RuntimeError("Twilio is down")
        failures = self._texts(PHONE_DAY * 2)
        message_user.return_value.text.side_effect = None

        self.assertEqual(failures, [status.HTTP_500_INTERNAL_SERVER_ERROR] * (PHONE_DAY * 2))
        self.assertEqual(self._post(ip="198.51.100.200", phone=PHONE), OK)

    def test_requests_for_an_unknown_screen_do_not_spend_the_phone_budget(self, message_user):
        """Nobody can use up a number's day without texting it."""
        self._texts(PHONE_DAY * 2, screen=UNKNOWN_SCREEN)

        message_user.return_value.text.assert_not_called()
        self.assertEqual(self._post(ip="198.51.100.200", phone=PHONE), OK)

    def test_a_typo_fix_is_a_different_budget(self, message_user):
        """A household retrying a mistyped number never hits the phone throttle."""
        self._texts(PHONE_HOUR)

        self.assertEqual(self._post(ip="198.51.100.200", phone=OTHER_PHONE), OK)

    def test_email_only_sends_do_not_spend_a_phone_budget(self, message_user):
        for i in range(PHONE_DAY + 1):
            self._post(ip=f"198.51.100.{i}", email="same@example.com")

        self.assertEqual(self._post(ip="198.51.100.200", phone=PHONE), OK)

    def test_throttled_request_sends_nothing(self, message_user):
        self._texts(PHONE_HOUR)
        message_user.reset_mock()

        self.assertEqual(self._post(ip="198.51.100.200", phone=PHONE), THROTTLED)
        message_user.assert_not_called()

    def test_a_throttled_request_logs_the_limit_and_not_who_hit_it(self, message_user):
        self._texts(PHONE_HOUR)

        with self.assertLogs("screener.throttles", level="WARNING") as logs:
            self._post(ip="198.51.100.200", phone=PHONE)

        logged = "\n".join(logs.output)
        self.assertIn("message_phone", logged)
        self.assertNotIn("3035550100", logged)
        self.assertNotIn("198.51.100.200", logged)

    # Sending

    def test_the_normal_flow_still_sends(self, message_user):
        self.assertEqual(self._post(phone=PHONE, language="es"), OK)

        message_user.assert_called_once_with(self.screen, "es")
        message_user.return_value.text.assert_called_once_with(PHONE, send_tests=True)

    def test_sends_the_number_the_throttle_counted(self, message_user):
        """The throttle keys on the E.164 form, so that is the form sent to Twilio."""
        self.assertEqual(self._post(phone="(303) 555-0100"), OK)

        message_user.return_value.text.assert_called_once_with(PHONE, send_tests=True)

    def test_a_non_string_phone_is_refused_and_not_sent(self, message_user):
        """A JSON number has no phone budget, so it must not reach Twilio either."""
        self.assertEqual(self._post(phone=13035550100), status.HTTP_400_BAD_REQUEST)

        message_user.assert_not_called()

    def test_an_invalid_phone_is_refused_and_not_sent(self, message_user):
        # A 7-digit number has no area code; every such number would share one key.
        self.assertEqual(self._post(phone="555-0100"), status.HTTP_400_BAD_REQUEST)

        message_user.assert_not_called()

    # Request body

    def test_a_json_body_is_read_whatever_the_declared_content_type(self, message_user):
        """Before the throttle, the view parsed the raw body as JSON regardless of
        Content-Type. Going through DRF's parsing must not narrow that."""
        body = json.dumps({"screen": str(self.screen.uuid), "phone": PHONE})

        response = self.client.post(URL, body, content_type="text/plain", REMOTE_ADDR="203.0.113.1")

        self.assertEqual(response.status_code, OK)
        message_user.return_value.text.assert_called_once_with(PHONE, send_tests=True)

    def test_a_body_that_is_not_an_object_is_a_400(self, message_user):
        response = self.client.post(URL, [PHONE], format="json", REMOTE_ADDR="203.0.113.1")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        message_user.assert_not_called()


@override_settings(CACHES=LOCAL_CACHE)
class SaveResultsPhoneKeyTests(SimpleTestCase):
    """The phone number never reaches the cache in a recoverable form."""

    def _ident(self, data) -> Optional[str]:
        return SaveResultsRateThrottle().phone_ident(mock.Mock(data=data))

    def test_key_does_not_contain_the_number(self):
        self.assertNotIn("3035550100", self._ident({"phone": PHONE}))

    def test_key_is_keyed_not_a_plain_hash(self):
        """An unkeyed sha256 of a 10-digit number can be reversed by enumeration."""
        ident = self._ident({"phone": PHONE})

        self.assertNotEqual(ident, hashlib.sha256(b"3035550100").hexdigest())
        self.assertNotEqual(ident, hashlib.sha256(PHONE.encode()).hexdigest())

    def test_formatting_variants_share_one_key(self):
        """The endpoint is reachable without the popup, so reformatting the same
        number must not buy a fresh budget."""
        variants = ["+13035550100", "3035550100", "+1 (303) 555-0100", "303-555-0100", "13035550100"]

        self.assertEqual({self._ident({"phone": phone}) for phone in variants}, {self._ident({"phone": PHONE})})

    def test_no_phone_has_no_key(self):
        self.assertIsNone(self._ident({"email": "a@example.com"}))
        self.assertIsNone(self._ident({"phone": None}))
        self.assertIsNone(self._ident([PHONE]))

    def test_an_invalid_phone_has_no_key(self):
        """The view refuses these with a 400 before sending anything, so there is
        no send to budget."""
        self.assertIsNone(self._ident({"phone": ""}))
        self.assertIsNone(self._ident({"phone": "555-0100"}))
        self.assertIsNone(self._ident({"phone": 3035550100}))

    def test_each_window_has_its_own_cache_key(self):
        scopes = SaveResultsRateThrottle.IP_SCOPES + SaveResultsRateThrottle.PHONE_SCOPES

        self.assertEqual(len({RateWindow(scope, "ident").key for scope in scopes}), len(scopes))

    def test_every_scope_has_a_usable_rate(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

        for scope in SaveResultsRateThrottle.IP_SCOPES + SaveResultsRateThrottle.PHONE_SCOPES:
            with self.subTest(scope=scope):
                self.assertTrue(is_valid_rate(rates[scope]))
