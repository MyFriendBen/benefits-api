"""Tests for RAGCache's handling of malformed sheet data.

_process() substitutes 0 for any income value it cannot parse. A county whose limits
all parse to 0 fails every income comparison, so the program silently disappears for
households in that county rather than raising.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from programs.programs.white_labels.co.rag.calculator import RAGCache

GOOD_ROW = ["Denver", "1,000", "2,000", "3,000"]
ALL_ZERO_ROW = ["Boulder", "n/a", "-", ""]
PARTIAL_ROW = ["Adams", "1,000", "oops", "3,000"]


class TestRAGCacheProcess(SimpleTestCase):
    def setUp(self):
        self.cache = RAGCache()

    def test_parses_county_rows(self):
        self.assertEqual(self.cache._process([GOOD_ROW]), {"Denver County": [1000, 2000, 3000]})

    def test_skips_short_rows(self):
        self.assertEqual(self.cache._process([["Denver"]]), {})

    @patch("programs.programs.white_labels.co.rag.calculator.capture_message")
    def test_all_zero_county_is_still_returned(self, _capture):
        """Unlike the AMI list, this is a per-county dict -- dropping the county
        entirely would be a larger behaviour change, so report instead."""
        result = self.cache._process([ALL_ZERO_ROW])

        self.assertEqual(result, {"Boulder County": [0, 0, 0]})

    @patch("programs.programs.white_labels.co.rag.calculator.capture_message")
    def test_all_zero_county_is_reported(self, capture):
        self.cache._process([ALL_ZERO_ROW])

        capture.assert_called_once()
        self.assertIn("Boulder County", capture.call_args.args[0])

    @patch("programs.programs.white_labels.co.rag.calculator.capture_message")
    def test_multiple_all_zero_counties_are_reported_once(self, capture):
        """Batched so a broken sheet does not emit one Sentry event per row."""
        self.cache._process([ALL_ZERO_ROW, ["Weld", "-", "-", "-"]])

        capture.assert_called_once()

    @patch("programs.programs.white_labels.co.rag.calculator.capture_message")
    def test_partially_zero_county_is_not_reported(self, capture):
        """Only an entirely-zero county makes the program unreachable."""
        result = self.cache._process([PARTIAL_ROW])

        self.assertEqual(result, {"Adams County": [1000, 0, 3000]})
        self.assertFalse(capture.called)

    @patch("programs.programs.white_labels.co.rag.calculator.capture_message")
    def test_good_rows_report_nothing(self, capture):
        self.cache._process([GOOD_ROW])

        self.assertFalse(capture.called)
