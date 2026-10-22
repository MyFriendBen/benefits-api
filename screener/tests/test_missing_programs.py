"""A degraded eligibility run is reported, and the response says it is incomplete.

Calculators are stubbed through `Program.eligibility`: what is under test is how the loop
handles what a calculator does, not any program's rule. A crash drops that one program
instead of 500ing the response; malformed screen data is reported once per screen; an
unanswered field stays quiet. A broken warning message costs only itself.
"""

from typing import Optional
from unittest.mock import MagicMock, patch

from django.test import TestCase

from programs.framework.base import Eligibility
from programs.models import FederalPoveryLimit, Program, ProgramCategory
from programs.programs.testing_fixtures.households import add_income, add_member, make_screen
from programs.util import Dependencies, DependencyError
from programs.warnings import warning_calculators
from programs.warnings.base import WarningCalculator
from screener.models import EligibilitySnapshot, Screen
from screener.tests.helpers import seed_program, seed_warning
from screener.views import eligibility_results

BROKEN = "test_broken"
WORKING = "test_working"


def eligible() -> Eligibility:
    e = Eligibility()
    e.eligible = True
    e.household_value = 100
    return e


class MissingProgramsTestCase(TestCase):
    def setUp(self) -> None:
        self.screen = make_screen(household_size=1)
        self.member = add_member(self.screen, age=30)
        category = ProgramCategory.objects.new_program_category(white_label="test", external_name="cash", icon="")
        year, _ = FederalPoveryLimit.objects.get_or_create(year="2025", defaults={"period": "2025"})

        seed_program(self.screen.white_label, BROKEN, WORKING)
        for program in Program.objects.filter(white_label=self.screen.white_label):
            program.active = True
            program.has_calculator = True
            program.category = category
            program.year = year
            program.save()

    def run_results(self, broken_raises: Optional[Exception] = None) -> dict:
        """Run the loop with `BROKEN` raising `broken_raises` (or eligible when None) and
        every other program eligible. Sentry is patched and returned for assertions."""

        def fake_eligibility(
            program_self: Program, screen: Screen, data: dict, missing_dependencies: Dependencies
        ) -> Eligibility:
            if program_self.name_abbreviated == BROKEN and broken_raises is not None:
                raise broken_raises
            return eligible()

        capture_exception, capture_message = MagicMock(), MagicMock()
        with patch.object(Program, "eligibility", fake_eligibility), patch(
            "screener.views.calc_pe_eligibility", return_value={"eligibility": {}, "_pe_data": {}}
        ), patch("screener.views.capture_exception", capture_exception), patch(
            "screener.views.capture_message", capture_message
        ):
            data, missing_programs, _, _ = eligibility_results(Screen.objects.get(pk=self.screen.pk))

        return {
            "published": sorted(entry["name_abbreviated"] for entry in data),
            "warnings": {entry["name_abbreviated"]: entry["warning_messages"] for entry in data},
            "missing_programs": missing_programs,
            "dropped": EligibilitySnapshot.objects.filter(screen=self.screen)
            .latest("submission_date")
            .dropped_programs,
            "capture_exception": capture_exception,
            "capture_message": capture_message,
        }


class TestACalculatorCrash(MissingProgramsTestCase):
    def test_drops_only_that_program(self) -> None:
        result = self.run_results(broken_raises=UnboundLocalError("monthly"))

        self.assertEqual(result["published"], [WORKING])
        self.assertTrue(result["missing_programs"])
        self.assertEqual(result["dropped"], {BROKEN: EligibilitySnapshot.DROPPED_CALCULATOR_ERROR})

    def test_is_reported_as_an_error_naming_the_program(self) -> None:
        error = RuntimeError("boom")
        result = self.run_results(broken_raises=error)

        result["capture_exception"].assert_called_once()
        self.assertIs(result["capture_exception"].call_args.args[0], error)
        self.assertEqual(result["capture_exception"].call_args.kwargs["level"], "error")
        message = result["capture_message"].call_args.kwargs
        self.assertEqual(message["level"], "error")
        self.assertEqual(message["fingerprint"], ["program-eligibility-failure", BROKEN])
        self.assertEqual(message["contexts"]["program"]["name_abbreviated"], BROKEN)


class TestAnUnansweredField(MissingProgramsTestCase):
    def test_drops_the_program_quietly(self) -> None:
        """Ordinary partial-screen input: flagged, never reported."""
        result = self.run_results(broken_raises=DependencyError())

        self.assertEqual(result["published"], [WORKING])
        self.assertTrue(result["missing_programs"])
        self.assertEqual(result["dropped"], {BROKEN: EligibilitySnapshot.DROPPED_MISSING_FIELD})
        result["capture_exception"].assert_not_called()
        result["capture_message"].assert_not_called()

    def test_a_null_income_frequency_is_not_reported(self) -> None:
        income = add_income(self.member, 1_000)
        income.frequency = None
        income.save()

        result = self.run_results()

        result["capture_message"].assert_not_called()
        self.assertFalse(result["missing_programs"])


class TestMalformedScreenData(MissingProgramsTestCase):
    def test_is_reported_once_and_flags_the_results(self) -> None:
        """Flagged whether or not a calculator declares the field: these stubs declare
        nothing, which is the case that used to compute from bad data in silence."""
        add_income(self.member, 1_000, frequency="fortnightly")
        add_income(self.member, 500, income_type="")

        result = self.run_results()

        self.assertTrue(result["missing_programs"])
        result["capture_message"].assert_called_once()
        message = result["capture_message"].call_args.kwargs
        self.assertEqual(message["level"], "error")
        self.assertEqual(message["fingerprint"], ["malformed-screen-data", "income_frequency", "income_type"])
        values = " ".join(message["contexts"]["malformed_data"]["values"])
        self.assertIn("'fortnightly'", values)

    def test_a_clean_screen_reports_nothing(self) -> None:
        add_income(self.member, 1_000)

        result = self.run_results()

        self.assertFalse(result["missing_programs"])
        result["capture_message"].assert_not_called()


class RaisingWarning(WarningCalculator):
    def calc(self) -> bool:
        raise RuntimeError("warning boom")


class TestABrokenWarning(MissingProgramsTestCase):
    """A warning is advisory: one that can't be evaluated is skipped and reported at
    warning level. The program's result is still right, so nothing is flagged incomplete."""

    def setUp(self) -> None:
        super().setUp()
        self.working = Program.objects.get(white_label=self.screen.white_label, name_abbreviated=WORKING)
        seed_warning(self.working, "_show", "Shown")

    def assert_skipped_quietly(self, result: dict) -> None:
        self.assertEqual(result["published"], [BROKEN, WORKING])
        self.assertEqual(len(result["warnings"][WORKING]), 1)
        self.assertFalse(result["missing_programs"])
        self.assertEqual(result["dropped"], {})
        message = result["capture_message"].call_args.kwargs
        self.assertEqual(message["level"], "warning")
        self.assertEqual(message["contexts"]["program"]["name_abbreviated"], WORKING)

    def test_an_unknown_calculator_name_is_skipped(self) -> None:
        seed_warning(self.working, "_renamed_away", "Never shown", external_name="renamed_away")

        result = self.run_results()

        self.assert_skipped_quietly(result)
        result["capture_message"].assert_called_once()
        self.assertEqual(
            result["capture_message"].call_args.kwargs["fingerprint"], ["warning-message-failure", "_renamed_away"]
        )
        result["capture_exception"].assert_not_called()

    def test_a_raising_calculator_is_skipped(self) -> None:
        seed_warning(self.working, "_test_raises", "Never shown", external_name="test_raises")

        with patch.dict(warning_calculators, {"_test_raises": RaisingWarning}):
            result = self.run_results()

        self.assert_skipped_quietly(result)
        result["capture_exception"].assert_called_once()
        self.assertEqual(result["capture_exception"].call_args.kwargs["level"], "warning")
