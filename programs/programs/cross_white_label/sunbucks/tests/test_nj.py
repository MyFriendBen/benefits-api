"""
NJ SUN Bucks (``NjSunBucks``): NJ's values, and one test per Test Scenario in the NJ spec
(``programs/cross_white_label/sunbucks/nj/sunbucks_nj_spec.md`` in program-ops).

The federal rules are tested against stand-in states in ``test_base.py``; these run the spec's
households end to end through real screener rows.

Scenarios 1-5 and 8-13 report SNAP, TANF, Head Start or school meals as a current benefit. NJ
has no Program row for some of them yet, so the tests seed a stand-in row with the right
``base_program`` so the rule is covered once the screener can send it.
"""

from datetime import date

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility
from programs.programs.cross_white_label.sunbucks.base import FOSTER_CHILD, SNAP, TANF, SunBucks
from programs.programs.cross_white_label.sunbucks.nj import NjSunBucks
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import Screen
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

VALUE_PER_CHILD = 120


class NjSunBucksTestCase(CustomCalculatorTestCase):
    calculator_class = NjSunBucks
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "07102"
    default_county = "Essex County"
    # Scenarios 10-13 date birth months against the July 2025 - August 2026 window.
    reference_date = date(2026, 10, 15)

    def household(self, size: int, head_wages: int = 0, head_age: int = 35) -> Screen:
        """A screen of `size` whose head earns `head_wages` a year. The test adds the rest."""
        screen = self.make_screen(household_size=size)
        self.add_member(screen, "headOfHousehold", head_age, yearly_income=head_wages)

        return screen

    def receive(self, screen: Screen, base_program: str) -> None:
        name = f"nj_{base_program}_stand_in"
        seed_program(self.white_label, name, base_program=base_program)
        _write_current_benefits(screen, [name])
        screen.invalidate_current_benefits_cache()

    def child_born(self, birth_year_month: date) -> Screen:
        """A Head Start household over the income limit, with one child born in `birth_year_month`."""
        screen = self.household(2, head_wages=200_000, head_age=45)
        self.add_member(screen, "child", None, birth_year_month=birth_year_month)
        self.receive(screen, "head_start")

        return screen

    def assert_eligible(self, eligibility: Eligibility, children: int = 1) -> None:
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, children * VALUE_PER_CHILD)

    def assert_ineligible(self, eligibility: Eligibility) -> None:
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)


class TestNjValues(NjSunBucksTestCase):
    def test_extends_the_base(self):
        self.assertTrue(issubclass(NjSunBucks, SunBucks))

    def test_program_code(self):
        self.assertEqual(NjSunBucks.program_code, "nj_sunbucks")

    def test_school_ages(self):
        self.assertEqual((NjSunBucks.min_school_age, NjSunBucks.max_school_age), (6, 16))
        self.assertEqual(NjSunBucks.school_age_window, (date(2025, 7, 1), date(2026, 8, 31)))

    def test_enrolls_snap_tanf_and_foster_children_automatically(self):
        self.assertEqual(NjSunBucks.enrolled_automatically, (SNAP, TANF, FOSTER_CHILD))


class TestCategorical(NjSunBucksTestCase):
    def test_scenario_1_head_start_household_with_two_school_age_children_and_an_adult(self):
        screen = self.household(3, head_wages=200_000)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 12)
        self.receive(screen, "head_start")

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility, children=2)
        self.assertEqual([m.value for m in eligibility.eligible_members], [0, 120, 120])

    def test_scenario_8_head_start_household_with_a_child_under_6(self):
        screen = self.household(2, head_wages=200_000)
        self.add_member(screen, "child", 4)
        self.receive(screen, "head_start")

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_9_child_with_medicaid_over_the_income_limit(self):
        screen = self.household(2, head_wages=200_000)
        child = self.add_member(screen, "child", 10)
        self.add_insurance(child, medicaid=True)

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(200_000, 40_034)])

    def test_scenario_18_no_qualifying_benefit_and_income_over_the_limit(self):
        screen = self.household(2, head_wages=200_000)
        self.add_member(screen, "child", 10)

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(200_000, 40_034)])


class TestEnrolledAutomatically(NjSunBucksTestCase):
    def test_scenario_2_snap_household(self):
        screen = self.household(3, head_wages=200_000)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 12)
        self.receive(screen, "snap")

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.must_not_have_benefit("SNAP")])

    def test_scenario_3_snap_household_under_the_income_limit(self):
        screen = self.household(2, head_wages=20_000)
        self.add_member(screen, "child", 10)
        self.receive(screen, "snap")

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_4_tanf_household(self):
        screen = self.household(2, head_wages=200_000)
        self.add_member(screen, "child", 10)
        self.receive(screen, "tanf")

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.must_not_have_benefit("TANF")])

    def test_scenario_5_tanf_reported_only_as_cash_assistance_income(self):
        screen = self.household(2, head_wages=200_000)
        self.add_member(screen, "child", 10)
        self.add_income(screen.get_head(), 3_000, "cashAssistance", "yearly")

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_6_foster_child(self):
        screen = self.household(2, head_wages=200_000, head_age=40)
        self.add_member(screen, "fosterChild", 10)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_7_foster_child_and_a_sibling_under_the_income_limit(self):
        screen = self.household(3, head_wages=20_000, head_age=40)
        self.add_member(screen, "fosterChild", 10)
        self.add_member(screen, "child", 12)

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual([m.value for m in eligibility.eligible_members], [0, 0, 120])


class TestSchoolAgeWindow(NjSunBucksTestCase):
    def test_scenario_10_turning_6_in_the_windows_last_month(self):
        self.assert_eligible(self.calculate(self.child_born(date(2020, 8, 1))))

    def test_scenario_11_one_month_too_young(self):
        self.assert_ineligible(self.calculate(self.child_born(date(2020, 9, 1))))

    def test_scenario_12_16_on_the_windows_first_day(self):
        self.assert_eligible(self.calculate(self.child_born(date(2008, 8, 1))))

    def test_scenario_13_already_17_on_the_windows_first_day(self):
        self.assert_ineligible(self.calculate(self.child_born(date(2008, 7, 1))))


class TestSchoolMealsAndIncome(NjSunBucksTestCase):
    def test_scenario_14_child_certified_for_school_meals(self):
        screen = self.household(1, head_wages=40_000, head_age=17)
        self.receive(screen, "nslp")

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.presumed_eligibility()])

    def test_scenario_15_well_under_the_income_limit(self):
        screen = self.household(1, head_wages=20_000, head_age=17)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_16_at_the_income_limit(self):
        screen = self.household(1, head_wages=29_526, head_age=17)

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility)
        self.assertEqual(eligibility.pass_messages, [messages.income(29_526, 29_526)])

    def test_scenario_17_one_dollar_over_the_income_limit(self):
        screen = self.household(1, head_wages=29_527, head_age=17)

        eligibility = self.calculate(screen)

        self.assert_ineligible(eligibility)
        self.assertEqual(eligibility.fail_messages, [messages.income(29_527, 29_526)])
