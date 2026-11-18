"""Tests for throttle rates read from the environment.

DRF parses a rate on every request and raises on one it cannot read, so a typo in
a config var would turn the endpoint it protects into a 500. These tests pin the
fallback that prevents that.
"""

import os
from unittest import mock

from django.test import SimpleTestCase
from rest_framework.throttling import SimpleRateThrottle

from benefits.throttle_config import is_valid_rate, throttle_rate

NAME = "MFB_TEST_THROTTLE_RATE"


class TestThrottleRate(SimpleTestCase):
    def _rate(self, value: str | None, default: str = "5/hour") -> str:
        """`throttle_rate` with the variable set to `value`, or unset for None."""
        with mock.patch.dict(os.environ):
            os.environ.pop(NAME, None)
            if value is not None:
                os.environ[NAME] = value
            return throttle_rate(NAME, default)

    def test_uses_the_default_when_unset(self):
        self.assertEqual(self._rate(None), "5/hour")

    def test_uses_the_environment_value(self):
        self.assertEqual(self._rate("50/hour"), "50/hour")
        self.assertEqual(self._rate(" 200/day "), "200/day")

    def test_a_blank_value_falls_back_to_the_default(self):
        self.assertEqual(self._rate(""), "5/hour")

    def test_an_unreadable_value_falls_back_to_the_default_and_says_so(self):
        for value in (
            "fifty/hour",
            "50",
            "50/fortnight",
            "/hour",
            "-5/hour",
            "50 per hour",
            "5/hour/x",
            "²/hour",
            "5/",
        ):
            with self.subTest(value=value):
                with self.assertLogs("benefits.throttle_config", level="WARNING") as logs:
                    self.assertEqual(self._rate(value), "5/hour")
                self.assertIn(NAME, logs.output[0])

    def test_accepts_exactly_what_drf_can_parse(self):
        """`is_valid_rate` is only useful if it agrees with the parser it guards."""
        throttle = SimpleRateThrottle.__new__(SimpleRateThrottle)

        for rate in ("1/s", "5/min", "100/hour", "500/day", "10/d"):
            with self.subTest(rate=rate):
                self.assertTrue(is_valid_rate(rate))
                throttle.parse_rate(rate)
