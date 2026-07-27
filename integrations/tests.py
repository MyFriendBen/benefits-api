"""Tests for the request-scoped external-API failure registry
(integrations/external_api_status.py)."""

from unittest.mock import patch

from django.test import SimpleTestCase

from integrations.external_api_status import (
    HUD,
    POLICY_ENGINE,
    get_external_api_failures,
    record_external_api_failure,
    report_external_api_failure,
    track_external_api_failures,
)


class TestExternalApiStatus(SimpleTestCase):
    def test_records_within_context(self):
        with track_external_api_failures():
            record_external_api_failure(POLICY_ENGINE)
            self.assertEqual(get_external_api_failures(), [POLICY_ENGINE])

    def test_returns_sorted_and_deduped(self):
        with track_external_api_failures():
            record_external_api_failure(POLICY_ENGINE)
            record_external_api_failure(HUD)
            record_external_api_failure(POLICY_ENGINE)  # duplicate is collapsed
            self.assertEqual(get_external_api_failures(), sorted([HUD, POLICY_ENGINE]))

    def test_no_op_without_context(self):
        # Recording outside a tracking context must not raise and must not leak.
        record_external_api_failure(POLICY_ENGINE)
        self.assertEqual(get_external_api_failures(), [])

    def test_context_resets_on_exit(self):
        with track_external_api_failures():
            record_external_api_failure(POLICY_ENGINE)
        # After the block, a fresh read sees nothing (the scope was reset).
        self.assertEqual(get_external_api_failures(), [])

    def test_nested_contexts_share_the_outer_scope(self):
        # A nested context reuses the outer set: failures recorded inside it stay visible
        # to the outer scope (only the outermost context initializes/resets).
        with track_external_api_failures():
            record_external_api_failure(POLICY_ENGINE)
            with track_external_api_failures():
                record_external_api_failure(HUD)
                self.assertEqual(get_external_api_failures(), sorted([HUD, POLICY_ENGINE]))
            # Inner failure remains after the nested block exits.
            self.assertEqual(get_external_api_failures(), sorted([HUD, POLICY_ENGINE]))
        # The outermost context resets everything on exit.
        self.assertEqual(get_external_api_failures(), [])


class TestReportExternalApiFailure(SimpleTestCase):
    """report_external_api_failure is the canonical "loud + flag" handling shared by the
    PolicyEngine and HUD integrations."""

    @patch("integrations.external_api_status.capture_message")
    @patch("integrations.external_api_status.capture_exception")
    def test_captures_exception_and_message_at_error_level(self, mock_capture_exception, mock_capture_message):
        boom = ValueError("boom")
        with track_external_api_failures():
            report_external_api_failure(HUD, "HUD is down", boom)
            self.assertEqual(get_external_api_failures(), [HUD])

        mock_capture_exception.assert_called_once_with(boom, level="error")
        mock_capture_message.assert_called_once_with("HUD is down", level="error")

    @patch("integrations.external_api_status.capture_message")
    @patch("integrations.external_api_status.capture_exception")
    def test_message_only_when_no_exception(self, mock_capture_exception, mock_capture_message):
        with track_external_api_failures():
            report_external_api_failure(POLICY_ENGINE, "no exception here")
            self.assertEqual(get_external_api_failures(), [POLICY_ENGINE])

        mock_capture_exception.assert_not_called()
        mock_capture_message.assert_called_once_with("no exception here", level="error")
