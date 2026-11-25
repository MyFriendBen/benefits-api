"""
NJ Temporary Disability Insurance, including Disability During Unemployment.

One test per spec §8 scenario, named for it, then the branches the scenarios don't reach:
a missing pregnancy answer, member-level routes, the value floor and the year fallback.
"""

from datetime import date
from typing import Optional
from unittest.mock import patch

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.nj.paid_leave import PAID_LEAVE_YEARS
from programs.programs.white_labels.nj.tdi.calculator import NjTdi
from programs.util import DependencyError
from screener.models import Screen


class NjTdiTestCase(CustomCalculatorTestCase):
    calculator_class = NjTdi
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "08608"
    default_county = "Mercer County"
    reference_date = date(2026, 11, 5)
    needs_program_row = False
    stores_age = False

    def person(
        self,
        age: int,
        wages: int = 0,
        unemployment: int = 0,
        workers_comp: int = 0,
        ssdi: int = 0,
        disabled: bool = False,
        pregnant: Optional[bool] = False,
    ) -> Screen:
        """A one-person household; every income is yearly, as the scenarios state them."""
        screen = self.make_screen()
        head = self.add_member(screen, "headOfHousehold", age, disabled=disabled, pregnant=pregnant)
        for amount, income_type in (
            (wages, "wages"),
            (unemployment, "unemployment"),
            (workers_comp, "workersComp"),
            (ssdi, "sSDisability"),
        ):
            if amount:
                self.add_income(head, amount, income_type, "yearly")
        return screen

    def assertValue(self, screen: Screen, value: int) -> None:
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assertIneligible(self, screen: Screen) -> None:
        self.assertFalse(self.calculate(screen).eligible)


class TestRegistration(NjTdiTestCase):
    def test_program_code(self):
        self.assertEqual(NjTdi.program_code, "nj_tdi")

    def test_constants(self):
        self.assertEqual(NjTdi.avg_days_paid, 70)
        figures = PAID_LEAVE_YEARS[2026]
        self.assertEqual(figures.earnings_test, 15_500)
        self.assertEqual(figures.max_weekly_rate, 1_119)

    def test_pregnant_is_not_a_dependency(self):
        self.assertNotIn("pregnant", NjTdi.dependencies)

    def test_missing_disabled_drops_the_program(self):
        screen = self.person(35, wages=52_000, disabled=True)
        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=("disabled",))


class TestSpecScenarios(NjTdiTestCase):
    def test_scenario_1_worker_with_a_disability_mid_range_wages(self):
        self.assertValue(self.person(35, wages=52_000, disabled=True), 8_500)

    def test_scenario_2_pregnant_worker_with_no_disability(self):
        self.assertValue(self.person(29, wages=40_000, pregnant=True), 6_530)

    def test_scenario_3_worker_with_a_disability_at_the_earnings_limit(self):
        self.assertValue(self.person(44, wages=15_500, disabled=True), 2_530)

    def test_scenario_4_worker_with_a_disability_one_dollar_under_the_earnings_limit(self):
        self.assertIneligible(self.person(44, wages=15_499, disabled=True))

    def test_scenario_5_healthy_worker_no_pregnancy(self):
        self.assertIneligible(self.person(35, wages=52_000))

    def test_scenario_6_worker_with_a_disability_already_on_workers_comp(self):
        # $400/week, stated weekly in the spec; entered as its yearly equivalent.
        self.assertIneligible(self.person(50, wages=52_000, workers_comp=400 * 52, disabled=True))

    def test_scenario_7_person_with_a_disability_no_wages_and_no_unemployment(self):
        self.assertIneligible(self.person(40, disabled=True))

    def test_scenario_8_high_earner_above_the_weekly_maximum(self):
        self.assertValue(self.person(45, wages=80_000, disabled=True), 11_190)

    def test_scenario_9_person_on_unemployment_who_becomes_disabled(self):
        self.assertValue(self.person(38, unemployment=26_000, disabled=True), 5_000)

    def test_scenario_10_person_on_unemployment_with_no_disability_or_pregnancy(self):
        self.assertIneligible(self.person(38, unemployment=500 * 52))

    def test_scenario_11_pregnant_person_on_unemployment(self):
        self.assertValue(self.person(30, unemployment=25_000, pregnant=True), 4_800)

    def test_scenario_12_worker_who_also_collects_partial_unemployment(self):
        self.assertValue(self.person(41, wages=52_000, unemployment=5_200, disabled=True), 8_500)

    def test_scenario_13_low_wage_worker_who_also_collects_unemployment(self):
        self.assertIneligible(self.person(40, wages=15_000, unemployment=5_000, disabled=True))

    def test_scenario_14_worker_with_a_disability_who_also_gets_ssdi(self):
        self.assertIneligible(self.person(52, wages=30_000, ssdi=18_000, disabled=True))

    def test_scenario_15_on_unemployment_with_a_disability_already_on_workers_comp(self):
        self.assertIneligible(self.person(47, unemployment=26_000, workers_comp=20_800, disabled=True))

    def test_scenario_16_on_unemployment_with_a_disability_who_also_gets_ssdi(self):
        self.assertIneligible(self.person(55, unemployment=26_000, ssdi=18_000, disabled=True))


class TestEdges(NjTdiTestCase):
    def test_unanswered_pregnancy_reads_as_not_pregnant(self):
        self.assertIneligible(self.person(29, wages=40_000, pregnant=None))

    def test_unanswered_pregnancy_still_values_a_disabled_worker(self):
        self.assertValue(self.person(35, wages=52_000, disabled=True, pregnant=None), 8_500)

    def test_ddu_is_not_capped(self):
        # floor(80,000 / 52) = 1,538 a week; the spec applies no DDU maximum.
        self.assertValue(self.person(38, unemployment=80_000, disabled=True), 15_380)

    def test_tiny_unemployment_is_floored_at_one_dollar(self):
        # floor(40 / 52) = 0 a week, which the results page would hide.
        self.assertValue(self.person(38, unemployment=40, disabled=True), 1)

    def test_each_eligible_member_is_valued(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", 35, disabled=True)
        self.add_income(head, 52_000, "wages", "yearly")
        spouse = self.add_member(screen, "spouse", 30, pregnant=True)
        self.add_income(spouse, 40_000, "wages", "yearly")
        healthy = self.add_member(screen, "child", 19)
        self.add_income(healthy, 30_000, "wages", "yearly")

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 8_500 + 6_530)
        self.assertEqual([m.eligible for m in e.eligible_members], [True, True, False])


class TestYearFallback(NjTdiTestCase):
    reference_date = date(2027, 2, 1)

    def test_a_year_without_figures_uses_the_latest_and_reports_it(self):
        screen = self.person(35, wages=52_000, disabled=True)

        with patch("programs.programs.white_labels.nj.paid_leave.capture_message") as capture:
            self.assertValue(screen, 8_500)

        capture.assert_called_once()
        self.assertIn("2027", capture.call_args.args[0])
