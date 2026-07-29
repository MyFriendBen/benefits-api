"""Tests for ACASubsidiesNC's county premium lookup.

member_value() used to raise KeyError for an unknown county. It now returns 0, which
the frontend filters out via its `value > 0` check -- so the program vanishes from
results with no error anywhere. The lookup must therefore report the miss.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from programs.programs.nc.nc_aca.calculator import ACACache, ACASubsidiesNC


class TestACACacheProcess(SimpleTestCase):
    def setUp(self):
        self.cache = ACACache()

    def test_parses_county_rows(self):
        self.assertEqual(self.cache._process([["Wake", "1,234.50"]]), {"Wake County": 1234.50})

    def test_skips_short_rows(self):
        self.assertEqual(self.cache._process([["Wake"]]), {})

    def test_skips_unparseable_values(self):
        self.assertEqual(self.cache._process([["Wake", "n/a"]]), {})

    def test_keeps_good_rows_alongside_bad(self):
        result = self.cache._process([["Wake", "n/a"], ["Durham", "999"]])

        self.assertEqual(result, {"Durham County": 999.0})


class TestACASubsidiesNCMemberValue(SimpleTestCase):
    def _calculator(self, county):
        calc = ACASubsidiesNC.__new__(ACASubsidiesNC)
        calc.screen = type("Screen", (), {"county": county})()
        return calc

    @patch.object(ACACache, "get_data", return_value={"Wake County": 100.0})
    def test_known_county_returns_annualised_value(self, _get_data):
        self.assertEqual(self._calculator("Wake County").member_value(None), 1200.0)

    @patch("programs.programs.nc.nc_aca.calculator.capture_message")
    @patch.object(ACACache, "get_data", return_value={"Wake County": 100.0})
    def test_unknown_county_returns_zero(self, _get_data, _capture):
        self.assertEqual(self._calculator("Nowhere County").member_value(None), 0)

    @patch("programs.programs.nc.nc_aca.calculator.capture_message")
    @patch.object(ACACache, "get_data", return_value={"Wake County": 100.0})
    def test_unknown_county_is_reported(self, _get_data, capture):
        self._calculator("Nowhere County").member_value(None)

        capture.assert_called_once()
        self.assertIn("Nowhere County", capture.call_args.args[0])

    @patch("programs.programs.nc.nc_aca.calculator.capture_message")
    @patch.object(ACACache, "get_data", return_value={})
    def test_empty_sheet_cache_is_reported(self, _get_data, capture):
        """The Redis-down case: get_data() falls back to {} and every county misses."""
        self.assertEqual(self._calculator("Wake County").member_value(None), 0)
        capture.assert_called_once()

    @patch("programs.programs.nc.nc_aca.calculator.capture_message")
    @patch.object(ACACache, "get_data", return_value={"Wake County": 100.0})
    def test_known_county_reports_nothing(self, _get_data, capture):
        self._calculator("Wake County").member_value(None)

        self.assertFalse(capture.called)
