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

        mock_capture_exception.assert_called_once_with(
            boom,
            level="error",
            contexts={"external_api": {"service": HUD}},
            fingerprint=["external-api-failure", HUD],
        )
        mock_capture_message.assert_called_once_with(
            "HUD is down",
            level="error",
            contexts={"external_api": {"service": HUD}},
            fingerprint=["external-api-failure", HUD],
        )

    @patch("integrations.external_api_status.capture_message")
    @patch("integrations.external_api_status.capture_exception")
    def test_message_only_when_no_exception(self, mock_capture_exception, mock_capture_message):
        with track_external_api_failures():
            report_external_api_failure(POLICY_ENGINE, "no exception here")
            self.assertEqual(get_external_api_failures(), [POLICY_ENGINE])

        mock_capture_exception.assert_not_called()
        mock_capture_message.assert_called_once_with(
            "no exception here",
            level="error",
            contexts={"external_api": {"service": POLICY_ENGINE}},
            fingerprint=["external-api-failure", POLICY_ENGINE],
        )

    @patch("integrations.external_api_status.capture_message")
    @patch("integrations.external_api_status.capture_exception")
    def test_caller_context_is_attached_to_both_events(self, mock_capture_exception, mock_capture_message):
        """Variable detail belongs in structured context, never in the message — Sentry
        groups capture_message by its text, so an interpolated screen id or response body
        would create one issue per screen."""
        boom = ValueError("boom")
        with track_external_api_failures():
            report_external_api_failure(HUD, "HUD is down", boom, context={"method": "Client.get", "detail": "500"})

        expected = {"external_api": {"service": HUD, "method": "Client.get", "detail": "500"}}
        self.assertEqual(mock_capture_exception.call_args.kwargs["contexts"], expected)
        self.assertEqual(mock_capture_message.call_args.kwargs["contexts"], expected)

    @patch("integrations.external_api_status.capture_message")
    @patch("integrations.external_api_status.capture_exception")
    def test_reports_once_per_service_per_run(self, mock_capture_exception, mock_capture_message):
        """A single screen makes several calls to the same integration (five HUD lookups
        across the MA calculators). An outage should produce one event, not one per call —
        the later ones carry no information the first didn't."""
        with track_external_api_failures():
            report_external_api_failure(HUD, "HUD is down", ValueError("first"))
            report_external_api_failure(HUD, "HUD is down", ValueError("second"))
            report_external_api_failure(HUD, "HUD is down", ValueError("third"))

            self.assertEqual(get_external_api_failures(), [HUD])

        self.assertEqual(mock_capture_exception.call_count, 1)
        self.assertEqual(mock_capture_message.call_count, 1)
        self.assertEqual(str(mock_capture_exception.call_args.args[0]), "first")

    @patch("integrations.external_api_status.capture_message")
    @patch("integrations.external_api_status.capture_exception")
    def test_dedupe_is_per_service_not_global(self, mock_capture_exception, mock_capture_message):
        with track_external_api_failures():
            report_external_api_failure(HUD, "HUD is down")
            report_external_api_failure(POLICY_ENGINE, "PE is down")

            self.assertEqual(get_external_api_failures(), sorted([HUD, POLICY_ENGINE]))

        self.assertEqual(mock_capture_message.call_count, 2)

    @patch("integrations.external_api_status.capture_message")
    @patch("integrations.external_api_status.capture_exception")
    def test_dedupe_resets_between_runs(self, mock_capture_exception, mock_capture_message):
        """The next screen's outage is news again — dedupe is scoped to the tracking
        context, not to the process."""
        for _ in range(2):
            with track_external_api_failures():
                report_external_api_failure(HUD, "HUD is down")

        self.assertEqual(mock_capture_message.call_count, 2)
