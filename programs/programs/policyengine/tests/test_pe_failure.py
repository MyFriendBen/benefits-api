"""Tests for calc_pe_eligibility's PolicyEngine failure handling (MFB-1246).

There is a single engine (the private household.api) and NO public fallback. Any
failure is surfaced loudly (Sentry error), recorded for the frontend, and degrades to
an empty PE result so the caller still computes the non-PolicyEngine calculators.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from screener.models import Screen, HouseholdMember, WhiteLabel
from programs.programs.policyengine import policy_engine as pe
from programs.programs.policyengine import engines as pe_engines_module
from programs.programs.policyengine.engines import PolicyEngineAPIError, PrivateApiSim
from integrations.external_api_status import (
    POLICY_ENGINE,
    get_external_api_failures,
    track_external_api_failures,
)


def _make_engine(name, log, *, raises=None):
    """Build a fake Sim-shaped engine. Appends its name to `log` on construction (so
    tests can assert which engines were tried), and optionally raises on construction to
    simulate a failed request."""

    class _Engine:
        method_name = name

        def __init__(self, data):
            log.append(name)
            if raises is not None:
                raise raises
            self.request_payload = data
            self.response_json = {"result": {}}

    return _Engine


class TestCalcPeEligibilityFailure(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=1,
            completed=False,
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        calc = MagicMock()
        calc.can_calc.return_value = True
        self.calculators = {"prog": calc}

    def _run(self, engines):
        """Run calc_pe_eligibility with `engines` as the engine list, everything else
        mocked. Returns (result, constructed, capture_message, failures)."""
        constructed = []
        engine_classes = [_make_engine(name, constructed, raises=raises) for name, raises in engines]

        with patch.object(pe, "pe_engines", engine_classes), patch.object(
            pe, "pe_input", return_value={}
        ), patch.object(pe, "all_eligibility", return_value={"prog": MagicMock()}), patch.object(
            pe, "capture_message"
        ) as capture_message, patch.object(
            pe, "capture_exception"
        ), track_external_api_failures():
            result = pe.calc_pe_eligibility(self.screen, self.calculators)
            failures = get_external_api_failures()

        return result, constructed, capture_message, failures

    @staticmethod
    def _error_messages(capture_message):
        return [c for c in capture_message.call_args_list if c.kwargs.get("level") == "error"]

    def test_success_serves_result_and_records_nothing(self):
        result, constructed, capture_message, failures = self._run([("Private Policy Engine API", None)])

        self.assertEqual(constructed, ["Private Policy Engine API"])
        self.assertIn("prog", result["eligibility"])
        self.assertEqual(self._error_messages(capture_message), [])
        self.assertEqual(failures, [])

    def test_400_failure_is_loud_recorded_and_degrades(self):
        result, _, capture_message, failures = self._run(
            [("Private Policy Engine API", PolicyEngineAPIError("bad payload", status_code=400))]
        )

        self.assertEqual(result["eligibility"], {})  # degraded -> caller runs custom calcs
        self.assertTrue(self._error_messages(capture_message))  # loud
        self.assertEqual(failures, [POLICY_ENGINE])  # reported to frontend

    def test_transient_failure_is_loud_recorded_and_degrades(self):
        # A timeout/5xx/auth failure is handled identically to a 400 — there's no fallback,
        # so every failure means PolicyEngine programs are unavailable.
        for status in (None, 503, 401):
            result, _, capture_message, failures = self._run(
                [("Private Policy Engine API", PolicyEngineAPIError("boom", status_code=status))]
            )
            self.assertEqual(result["eligibility"], {}, status)
            self.assertTrue(self._error_messages(capture_message), status)
            self.assertEqual(failures, [POLICY_ENGINE], status)

    def test_non_policyengine_exception_also_degrades(self):
        # A non-PolicyEngineAPIError (e.g. bad response shape) is caught by the generic
        # handler and treated the same: loud, recorded, degraded.
        result, _, capture_message, failures = self._run([("Private Policy Engine API", ValueError("weird"))])

        self.assertEqual(result["eligibility"], {})
        self.assertTrue(self._error_messages(capture_message))
        self.assertEqual(failures, [POLICY_ENGINE])

    def test_no_fallback_second_engine_never_tried(self):
        # Even if a second engine were present, a first-engine failure returns immediately
        # (degraded) — we never silently try another endpoint.
        result, constructed, _, failures = self._run(
            [
                ("Private Policy Engine API", PolicyEngineAPIError("down", status_code=500)),
                ("Some Other Engine", None),  # would succeed, but must NOT be reached
            ]
        )

        self.assertEqual(constructed, ["Private Policy Engine API"])
        self.assertEqual(result["eligibility"], {})
        self.assertEqual(failures, [POLICY_ENGINE])

    def test_pe_engines_is_only_the_private_endpoint(self):
        # Lock the removal of the public fallback: the private household.api is the only
        # configured engine.
        self.assertEqual(pe_engines_module.pe_engines, [PrivateApiSim])
