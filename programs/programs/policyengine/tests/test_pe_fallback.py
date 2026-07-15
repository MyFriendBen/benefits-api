"""Tests for calc_pe_eligibility's engine fallback behavior (MFB-1246):
- a 400 fails loudly and does NOT fall back (the payload is malformed and every
  endpoint would reject it identically);
- a transient failure falls back to the next engine, and a successful fallback is
  surfaced loudly (error level);
- when every engine fails, the PolicyEngine failure is recorded for the frontend.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from screener.models import Screen, HouseholdMember, WhiteLabel
from programs.programs.policyengine import policy_engine as pe
from programs.programs.policyengine.engines import PolicyEngineAPIError
from integrations.external_api_status import (
    POLICY_ENGINE,
    get_external_api_failures,
    track_external_api_failures,
)


def _make_engine(name, log, *, raises=None):
    """Build a fake Sim subclass-shaped engine. Appends its name to `log` on
    construction (so tests can assert whether the fallback engine was tried), and
    optionally raises on construction to simulate a failed request."""

    class _Engine:
        method_name = name

        def __init__(self, data):
            log.append(name)
            if raises is not None:
                raise raises
            self.request_payload = data
            self.response_json = {"result": {}}

    return _Engine


class TestCalcPeEligibilityFallback(TestCase):
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
        # Instantiate the fake engine classes bound to `constructed`.
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

    def test_400_fails_loud_and_does_not_fall_back(self):
        result, constructed, capture_message, failures = self._run(
            [
                ("Private Policy Engine API", PolicyEngineAPIError("bad payload", status_code=400)),
                ("Policy Engine API", None),  # would succeed, but must NOT be reached
            ]
        )

        # Only the primary was tried; no silent fallback on a 400.
        self.assertEqual(constructed, ["Private Policy Engine API"])
        self.assertEqual(result["eligibility"], {})
        # Surfaced loudly (error, not warning) and recorded for the frontend.
        self.assertTrue(self._error_messages(capture_message))
        self.assertEqual(failures, [POLICY_ENGINE])

    def test_transient_failure_falls_back_and_is_loud(self):
        result, constructed, capture_message, failures = self._run(
            [
                ("Private Policy Engine API", PolicyEngineAPIError("timeout", status_code=None)),
                ("Policy Engine API", None),  # fallback succeeds
            ]
        )

        # Both engines tried; fallback served the result.
        self.assertEqual(constructed, ["Private Policy Engine API", "Policy Engine API"])
        self.assertIn("prog", result["eligibility"])
        # A successful fallback now implies degraded/auth issues -> error level.
        self.assertTrue(self._error_messages(capture_message))
        # The public fallback can't honor the resolved version, so a served fallback is
        # flagged to the frontend (banner) rather than presented silently.
        self.assertEqual(failures, [POLICY_ENGINE])

    def test_5xx_falls_back(self):
        _, constructed, _, failures = self._run(
            [
                ("Private Policy Engine API", PolicyEngineAPIError("boom", status_code=503)),
                ("Policy Engine API", None),
            ]
        )
        self.assertEqual(constructed, ["Private Policy Engine API", "Policy Engine API"])
        self.assertEqual(failures, [POLICY_ENGINE])

    def test_all_engines_fail_records_failure(self):
        result, constructed, _, failures = self._run(
            [
                ("Private Policy Engine API", PolicyEngineAPIError("timeout", status_code=None)),
                ("Policy Engine API", PolicyEngineAPIError("timeout", status_code=None)),
            ]
        )

        self.assertEqual(constructed, ["Private Policy Engine API", "Policy Engine API"])
        self.assertEqual(result["eligibility"], {})
        self.assertEqual(failures, [POLICY_ENGINE])

    def test_primary_success_no_fallback_no_record(self):
        result, constructed, capture_message, failures = self._run(
            [
                ("Private Policy Engine API", None),  # primary succeeds
                ("Policy Engine API", None),
            ]
        )

        # Fallback never constructed; no loud error; nothing reported.
        self.assertEqual(constructed, ["Private Policy Engine API"])
        self.assertNotEqual(result["eligibility"], {})
        self.assertEqual(self._error_messages(capture_message), [])
        self.assertEqual(failures, [])
