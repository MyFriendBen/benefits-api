"""An active program row with no calculator registered under its name must not take the
results page down: it is reported and left out, and every other program still calculates."""

from unittest.mock import patch

from django.test import TestCase

from programs.models import FederalPoveryLimit, Program, ProgramCategory
from programs.programs.testing_fixtures.households import add_member
from programs.util import UnregisteredCalculatorError
from screener.models import EligibilitySnapshot, Screen, WhiteLabel
from screener.views import eligibility_results


class TestUnregisteredCalculator(TestCase):
    def setUp(self) -> None:
        # get_or_create: a migrated test database already seeds the Colorado white label.
        self.co, _ = WhiteLabel.objects.get_or_create(code="co", defaults={"name": "Colorado", "state_code": "CO"})
        # A name nothing seeds: migration 0172 creates the shared "cash" category, so a test
        # that creates it too errors under a migrated test database.
        category = ProgramCategory.objects.new_program_category(
            white_label=None, external_name="unregistered_calculator_test", icon=""
        )
        fpl = FederalPoveryLimit.objects.create(year="2025", period="2025")
        # A real MFB calculator the household qualifies for, beside a row with none.
        self.trump_account = self._program("federal_trump_account", category, fpl)
        self.orphan = self._program("retired_credit", category, fpl)
        self.screen = Screen.objects.create(white_label=self.co, zipcode="80202", household_size=2, completed=False)
        add_member(self.screen, "headOfHousehold", age=30)
        add_member(self.screen, "child", age=1)

    def _program(self, name: str, category: ProgramCategory, fpl: FederalPoveryLimit) -> Program:
        program = Program.objects.new_program("co", name)
        program.active = True
        program.has_calculator = True
        program.category = category
        program.year = fpl
        program.save()
        return program

    def test_eligibility_raises_a_dependency_error_and_reports_it(self) -> None:
        with patch("programs.models.capture_message") as report:
            with self.assertRaises(UnregisteredCalculatorError) as raised:
                self.orphan.eligibility(self.screen, {}, self.screen.missing_fields())

        self.assertEqual(
            (raised.exception.white_label_code, raised.exception.name_abbreviated), ("co", "retired_credit")
        )
        report.assert_called_once()
        self.assertIn("co/retired_credit", report.call_args.args[0])

    def test_the_other_programs_still_calculate_and_the_row_is_recorded_as_dropped(self) -> None:
        with patch("programs.models.capture_message"), patch(
            "screener.views.calc_pe_eligibility", return_value={"eligibility": {}, "_pe_data": {}}
        ):
            data, missing_programs, _, _ = eligibility_results(self.screen)

        self.assertEqual([p["name_abbreviated"] for p in data], ["federal_trump_account"])
        self.assertTrue(data[0]["eligible"])
        self.assertTrue(missing_programs)
        snapshot = EligibilitySnapshot.objects.get(screen=self.screen)
        self.assertEqual(snapshot.dropped_programs, {"retired_credit": EligibilitySnapshot.DROPPED_NO_CALCULATOR})
