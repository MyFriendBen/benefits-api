"""Tests for BoulderAmiCache's handling of malformed sheet data.

_process() substitutes 0 for any value it cannot parse. A list of zeros is truthy, so
GoogleSheetsCache.get_data()'s `if not data` guard would happily cache it for 24h and
write it to the 7-day stale key. Every income comparison would then run against a
limit of 0, so nobody qualifies -- and because the frontend drops programs whose value
is not > 0, the program simply disappears rather than erroring.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from programs.programs.white_labels.co.nf.calculator import BoulderAmiCache

GOOD_ROW = [["1,000", "2,000", "3,000", "4,000", "5,000", "6,000", "7,000", "8,000"]]
ALL_MALFORMED_ROW = [["", "-", "n/a", "", "", "", "", ""]]
PARTIAL_ROW = [["1,000", "oops", "3,000", "4,000", "5,000", "6,000", "7,000", "8,000"]]


class TestBoulderAmiCacheProcess(SimpleTestCase):
    def setUp(self):
        self.cache = BoulderAmiCache()

    def test_parses_a_good_row(self):
        self.assertEqual(self.cache._process(GOOD_ROW), [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000])

    def test_empty_raw_data_returns_empty(self):
        self.assertEqual(self.cache._process([]), [])

    @patch("programs.programs.white_labels.co.nf.calculator.capture_message")
    def test_all_zero_result_is_not_returned_for_caching(self, _capture):
        """Returning [] routes get_data() through the stale/fallback path instead."""
        self.assertEqual(self.cache._process(ALL_MALFORMED_ROW), [])

    @patch("programs.programs.white_labels.co.nf.calculator.capture_message")
    def test_all_zero_result_is_reported(self, capture):
        self.cache._process(ALL_MALFORMED_ROW)

        self.assertTrue(capture.called)
        self.assertEqual(capture.call_args_list[-1].kwargs["level"], "error")

    @patch("programs.programs.white_labels.co.nf.calculator.capture_message")
    def test_partially_malformed_row_is_kept_but_reported(self, capture):
        """One bad cell is recoverable, so keep the row -- but say so."""
        result = self.cache._process(PARTIAL_ROW)

        self.assertEqual(result, [1000, 0, 3000, 4000, 5000, 6000, 7000, 8000])
        self.assertTrue(capture.called)
        self.assertEqual(capture.call_args_list[0].kwargs["level"], "warning")

    @patch("programs.programs.white_labels.co.nf.calculator.capture_message")
    def test_good_row_reports_nothing(self, capture):
        self.cache._process(GOOD_ROW)

        self.assertFalse(capture.called)

    def test_all_zero_result_would_have_been_cacheable(self):
        """Documents why the guard exists: the naive result passes get_data()'s check."""
        naive_result = [0] * 8

        self.assertTrue(naive_result, "a list of zeros is truthy, so `if not data` would not catch it")
