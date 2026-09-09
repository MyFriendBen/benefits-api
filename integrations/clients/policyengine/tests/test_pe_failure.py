"""Tests for calc_pe_eligibility's PolicyEngine failure handling (MFB-1246).

There is a single engine (the private household.api) and NO public fallback. Any
failure is surfaced loudly (Sentry error), recorded for the frontend, and degrades to
an empty PE result so the caller still computes the non-PolicyEngine calculators.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from programs.util import ProgramConfigurationError
from screener.models import Screen, HouseholdMember, WhiteLabel
from integrations.clients.policyengine import policy_engine as pe
from integrations.clients.policyengine import engines as pe_engines_module
from integrations.clients.policyengine.engines import PolicyEngineAPIError, PrivateApiSim
from programs.framework.pe_dependencies.base import ConflictingDependencyError
from programs.framework.pe_dependencies.payload import Bucket, PayloadPlan
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

        plan = PayloadPlan(payload={}, buckets=[Bucket(program_indexes=[0])])

        with patch.object(pe, "pe_engines", engine_classes), patch.object(
            pe, "build_pe_input", return_value=plan
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

    def test_payload_assembly_failure_degrades_instead_of_raising(self):
        """A dependency crashing on screen data it can't handle (an unconvertible expense
        frequency raises UnboundLocalError in `Expense.yearly()`) must cost the screen its
        PolicyEngine programs, not 500 the whole response."""
        error = UnboundLocalError("cannot access local variable 'yearly'")

        with patch.object(pe, "build_pe_input", side_effect=error), patch.object(
            pe, "capture_message"
        ) as capture_message, patch.object(pe, "capture_exception") as capture_exception, track_external_api_failures():
            result = pe.calc_pe_eligibility(self.screen, self.calculators)
            failures = get_external_api_failures()

        self.assertEqual(result["eligibility"], {})
        capture_exception.assert_called_once_with(error, level="error")
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

    def test_status_code_is_in_the_sentry_message(self):
        # PolicyEngineAPIError has always carried the status; it belongs in the message so a
        # 400 (our payload) is distinguishable from a 5xx (theirs) in the Sentry issue list.
        _, _, capture_message, _ = self._run(
            [("Private Policy Engine API", PolicyEngineAPIError("bad payload", status_code=400))]
        )

        self.assertIn("(HTTP 400)", self._error_messages(capture_message)[0].args[0])

    def test_no_status_code_leaves_the_message_clean(self):
        # A timeout or DNS failure never got a response, so there is no status to report.
        _, _, capture_message, _ = self._run([("Private Policy Engine API", PolicyEngineAPIError("timed out"))])

        self.assertNotIn("HTTP", self._error_messages(capture_message)[0].args[0])


class TestPayloadAssemblyFailure(TestCase):
    """Payload assembly failing degrades like any other PolicyEngine failure.

    It used to escape `calc_pe_eligibility` and 500 the whole response, so a screen lost even
    the programs that never touch PolicyEngine.
    """

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

    def _run(self, error):
        """Run calc_pe_eligibility with payload assembly raising `error`."""
        with patch.object(pe, "build_pe_input", side_effect=error), patch.object(
            pe, "capture_message"
        ) as capture_message, patch.object(pe, "capture_exception"), track_external_api_failures():
            result = pe.calc_pe_eligibility(self.screen, self.calculators)
            failures = get_external_api_failures()

        return result, capture_message, failures

    def test_unexpected_error_degrades_instead_of_500ing(self):
        result, capture_message, failures = self._run(KeyError("snap_if_takes_up"))

        self.assertEqual(result["eligibility"], {})  # caller still runs the custom calcs
        self.assertTrue([c for c in capture_message.call_args_list if c.kwargs.get("level") == "error"])
        self.assertEqual(failures, [POLICY_ENGINE])  # -> banner on the results page

    def test_misconfigured_program_degrades(self):
        # The typed guard a program with no FederalPoveryLimit hits if it ever reaches
        # payload assembly (the pre-filter should have dropped it first).
        result, _, failures = self._run(ProgramConfigurationError("no period"))

        self.assertEqual(result["eligibility"], {})
        self.assertEqual(failures, [POLICY_ENGINE])

    def test_dependency_conflict_is_reported_to_the_frontend(self):
        # The conflict arm logged loudly but did not record the failure, so the user got a
        # short results page with no banner explaining it.
        result, capture_message, failures = self._run(ConflictingDependencyError("age", 35, 36))

        self.assertEqual(result["eligibility"], {})
        self.assertTrue([c for c in capture_message.call_args_list if c.kwargs.get("level") == "error"])
        self.assertEqual(failures, [POLICY_ENGINE])

    def test_worker_teardown_still_propagates(self):
        # SystemExit is BaseException: `except Exception` must not turn a dying worker into a
        # logged payload failure.
        with patch.object(pe, "build_pe_input", side_effect=SystemExit()), patch.object(
            pe, "capture_message"
        ), patch.object(pe, "capture_exception"), track_external_api_failures():
            with self.assertRaises(SystemExit):
                pe.calc_pe_eligibility(self.screen, self.calculators)


class TestUnconfiguredProgramIsDropped(TestCase):
    """A PolicyEngine program with no FederalPoveryLimit costs only itself.

    Every variable it asks for is keyed by period, and there is no period without a year, so
    it cannot be part of a request. Dropping it before assembly keeps the failure the size of
    the misconfiguration; reaching `pe_period` instead would raise mid-build and cost every
    PolicyEngine program on the screen its result.
    """

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

    @staticmethod
    def _calculator(year):
        calc = MagicMock()
        calc.can_calc.return_value = True
        calc.program.year = year
        return calc

    def test_unconfigured_program_is_dropped_and_reported(self):
        calculators = {"broken": self._calculator(None)}

        with patch.object(pe, "build_pe_input") as build, patch.object(
            pe, "capture_message"
        ) as capture_message, track_external_api_failures():
            result = pe.calc_pe_eligibility(self.screen, calculators)
            failures = get_external_api_failures()

        self.assertEqual(result["eligibility"], {})
        build.assert_not_called()  # no request is built at all
        self.assertIn("broken", capture_message.call_args_list[0].args[0])
        # Not an external-API failure: PolicyEngine was never asked. The program is simply
        # absent, which the caller already reports as `missing_programs`.
        self.assertEqual(failures, [])

    def test_its_siblings_still_calculate(self):
        calculators = {"broken": self._calculator(None), "fine": self._calculator(MagicMock())}
        plan = PayloadPlan(payload={}, buckets=[Bucket(program_indexes=[0])])

        with patch.object(pe, "build_pe_input", return_value=plan) as build, patch.object(
            pe, "pe_engines", [_make_engine("Private Policy Engine API", [])]
        ), patch.object(pe, "all_eligibility", return_value={"fine": MagicMock()}), patch.object(
            pe, "capture_message"
        ), track_external_api_failures():
            result = pe.calc_pe_eligibility(self.screen, calculators)

        self.assertEqual(list(result["eligibility"]), ["fine"])
        self.assertEqual(len(build.call_args.args[1]), 1)  # only the configured program
