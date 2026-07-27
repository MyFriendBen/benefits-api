"""Locks the three ways a degraded eligibility run must reach `missing_programs`.

`missing_programs` is the only signal the response carries that results are incomplete.
It used to be set for exactly two reasons — a DependencyError from a custom calculator,
or a PolicyEngine program absent from the PE result — which left three degradations
completely silent: an external integration (HUD) failing under a calculator that
swallows the error, a calculator crashing on data the dependency gate let through, and
screen data that is malformed rather than null. These tests pin all of them.
"""

from unittest.mock import patch

from django.test import TestCase

from integrations.external_api_status import HUD, record_external_api_failure, track_external_api_failures
from programs.models import Program, ProgramCategory
from programs.programs.calc import Eligibility, ProgramCalculator
from programs.util import DependencyError
from screener.models import Screen, HouseholdMember, WhiteLabel, IncomeStream
from screener.views import eligibility_results


class BoomCalculator(ProgramCalculator):
    """Stands in for a calculator that crashes on data the gate let through — e.g. an
    income row whose frequency is unrecognized, so IncomeStream.yearly() falls through
    every branch and raises UnboundLocalError."""

    def household_eligible(self, e: Eligibility):
        raise UnboundLocalError("cannot access local variable 'yearly'")


class SkipCalculator(ProgramCalculator):
    """Stands in for the ordinary partial-screen path."""

    def calc(self) -> Eligibility:
        raise DependencyError()


class FineCalculator(ProgramCalculator):
    amount = 100


class MissingProgramsTestBase(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            household_assets=0,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            student=False,
            pregnant=False,
            visually_impaired=False,
            disabled=False,
            long_term_disability=False,
        )

    def _seed_program(self, name_abbreviated: str) -> Program:
        """new_program() creates an inactive, uncategorized row; eligibility_results only
        looks at active + categorized + has_calculator programs."""
        if not hasattr(self, "_category"):
            self._category = ProgramCategory.objects.new_program_category(self.white_label.code, "test-category", None)

        program = Program.objects.new_program(self.white_label.code, name_abbreviated)
        program.active = True
        program.has_calculator = True
        program.category = self._category
        program.save()
        return program

    def _run(self):
        """Run eligibility_results inside a tracking context, as the results view does."""
        with track_external_api_failures():
            _programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)
        return missing_programs


class TestExternalApiFailureSetsMissingPrograms(MissingProgramsTestBase):
    def test_recorded_hud_failure_sets_missing_programs(self):
        """HUD-backed calculators catch HudIncomeClientError and degrade to "not eligible
        (income limit unknown)", so nothing raises and no program is skipped — the
        recorded failure is the only trace, and it has to flip the flag."""
        with track_external_api_failures():
            record_external_api_failure(HUD)
            _programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        self.assertTrue(missing_programs)

    def test_no_failure_leaves_flag_false(self):
        self.assertFalse(self._run())


class TestCalculatorCrashSetsMissingPrograms(MissingProgramsTestBase):
    def test_crash_is_reported_and_flagged_not_fatal(self):
        program = self._seed_program("boom")

        with patch.dict("programs.models.calculators", {"boom": BoomCalculator}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    missing_programs = self._run()

        self.assertTrue(missing_programs)
        # Loud: both the exception and a human-readable context line, at error level.
        self.assertEqual(mock_capture_exception.call_args.kwargs, {"level": "error"})
        self.assertIsInstance(mock_capture_exception.call_args.args[0], UnboundLocalError)
        self.assertIn(program.name_abbreviated, mock_capture_message.call_args.args[0])
        self.assertEqual(mock_capture_message.call_args.kwargs, {"level": "error"})

    def test_one_crashing_program_does_not_lose_the_others(self):
        """The whole point: previously this 500'd and the user got zero results."""
        self._seed_program("boom")
        self._seed_program("fine")

        with patch.dict(
            "programs.models.calculators",
            {"boom": BoomCalculator, "fine": FineCalculator},
            clear=False,
        ):
            with patch("screener.views.capture_exception"), patch("screener.views.capture_message"):
                with track_external_api_failures():
                    programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        self.assertTrue(missing_programs)
        returned = {p["short_name"] for p in programs}
        self.assertIn("fine", returned)
        self.assertNotIn("boom", returned)

    def test_dependency_error_stays_quiet(self):
        """An unanswered question is not a defect — flag the response, but don't page
        anyone."""
        self._seed_program("skip")

        with patch.dict("programs.models.calculators", {"skip": SkipCalculator}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    missing_programs = self._run()

        self.assertTrue(missing_programs)
        mock_capture_exception.assert_not_called()
        mock_capture_message.assert_not_called()


class TestMalformedDataSetsMissingPrograms(MissingProgramsTestBase):
    def test_malformed_screen_data_is_reported_and_flagged(self):
        """Set independently of which calculators happen to declare the field: with no
        calculator declaring income_frequency, nothing would raise DependencyError, yet
        the run is still degraded."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=100,
            frequency="fortnightly",
        )

        with patch("screener.views.capture_message") as mock_capture_message:
            missing_programs = self._run()

        self.assertTrue(missing_programs)
        message = mock_capture_message.call_args.args[0]
        self.assertIn("income_frequency", message)
        self.assertIn("fortnightly", message)
        self.assertEqual(mock_capture_message.call_args.kwargs, {"level": "error"})

    def test_null_data_does_not_trigger_the_malformed_report(self):
        """A null income row is ordinary partial input: it still gates programs that
        declare it, but must not fire a Sentry error."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type=None, amount=None, frequency=None
        )

        with patch("screener.views.capture_message") as mock_capture_message:
            self._run()

        mock_capture_message.assert_not_called()
