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

SENTRY_EXCEPTION = "integrations.external_api_status.capture_exception"
SENTRY_MESSAGE = "integrations.external_api_status.capture_message"


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
    def test_records_and_sends_one_error_event_each(self):
        error = RuntimeError("down")
        with patch(SENTRY_EXCEPTION) as exc, patch(SENTRY_MESSAGE) as msg, track_external_api_failures():
            report_external_api_failure(HUD, "HUD failed.", error, context={"method": "lookup"})
            failures = get_external_api_failures()

        self.assertEqual(failures, [HUD])
        exc.assert_called_once()
        self.assertIs(exc.call_args.args[0], error)
        self.assertEqual(exc.call_args.kwargs["level"], "error")
        msg.assert_called_once()
        self.assertEqual(msg.call_args.args[0], "HUD failed.")
        self.assertEqual(msg.call_args.kwargs["level"], "error")
        self.assertEqual(msg.call_args.kwargs["fingerprint"], ["external-api-failure", HUD])
        self.assertEqual(msg.call_args.kwargs["contexts"]["external_api"], {"service": HUD, "method": "lookup"})

    def test_reports_once_per_service_per_run(self):
        """An outage fails every call a screen makes; the first event says it all."""
        with patch(SENTRY_EXCEPTION) as exc, patch(SENTRY_MESSAGE) as msg, track_external_api_failures():
            for _ in range(5):
                report_external_api_failure(HUD, "HUD failed.", RuntimeError("down"))
            report_external_api_failure(POLICY_ENGINE, "PE failed.", RuntimeError("down"))
            failures = get_external_api_failures()

        self.assertEqual(failures, sorted([HUD, POLICY_ENGINE]))
        self.assertEqual(exc.call_count, 2)
        self.assertEqual(msg.call_count, 2)

    def test_without_an_exception_sends_only_the_message(self):
        with patch(SENTRY_EXCEPTION) as exc, patch(SENTRY_MESSAGE) as msg, track_external_api_failures():
            report_external_api_failure(HUD, "HUD failed.")

        exc.assert_not_called()
        msg.assert_called_once()

    def test_outside_a_context_still_reports_to_sentry(self):
        """Management commands and shell use have no run to flag, but the failure is real."""
        with patch(SENTRY_EXCEPTION) as exc, patch(SENTRY_MESSAGE) as msg:
            report_external_api_failure(HUD, "HUD failed.", RuntimeError("down"))

        exc.assert_called_once()
        msg.assert_called_once()
        self.assertEqual(get_external_api_failures(), [])
