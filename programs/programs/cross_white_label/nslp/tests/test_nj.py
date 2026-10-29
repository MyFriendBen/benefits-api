"""
NJ National School Lunch Program (``NjNslp``): NJ's values, and one test per Test Scenario in the
NJ spec (``programs/cross_white_label/nslp/nj/nslp_nj_spec.md`` in program-ops).

The federal rules are tested against a stand-in state in ``test_mfb_base.py``; these run the
spec's households end to end through real screener rows.

The spec states values in cents ($871.20, $799.20). The API reports whole dollars, so each
student is worth 871 or 799 here.

Scenarios 14, 15, 17, 18 and 22 report SNAP, TANF, Head Start or WIC as a current benefit. NJ has
no Program row for some of them yet, so the tests seed a stand-in row with the right
``base_program``.
"""

from decimal import Decimal

from programs.framework.base import Eligibility
from programs.models import Program
from programs.programs.cross_white_label.nslp.mfb_base import FREE, REDUCED_PRICE, NationalSchoolLunchProgram
from programs.programs.cross_white_label.nslp.nj import NJEIE, NjNslp
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import Screen
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

# $4.84 a lunch x 180 days = $871.20; $4.44 x 180 = $799.20.
STUDENT_VALUE = 871
REDUCED_PRICE_OVER_18_VALUE = 799


class NjNslpTestCase(CustomCalculatorTestCase):
    calculator_class = NjNslp
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "08608"
    default_county = "Mercer County"

    def household(self, size: int, head_age: int, head_wages: int = 0, head_monthly_wages: int = 0) -> Screen:
        """A screen of `size` whose head earns the stated wages. The test adds the rest."""
        screen = self.make_screen(household_size=size)
        self.add_member(
            screen, "headOfHousehold", head_age, yearly_income=head_wages, monthly_income=head_monthly_wages
        )

        return screen

    def receive(self, screen: Screen, base_program: str) -> None:
        name = f"nj_{base_program}_stand_in"
        seed_program(self.white_label, name, base_program=base_program)
        _write_current_benefits(screen, [name])
        screen.invalidate_current_benefits_cache()

    def assert_eligible(self, eligibility: Eligibility, value: int) -> None:
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, value)

    def assert_ineligible(self, eligibility: Eligibility) -> None:
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)


class TestNjValues(NjNslpTestCase):
    def test_extends_the_base(self):
        self.assertTrue(issubclass(NjNslp, NationalSchoolLunchProgram))

    def test_program_code(self):
        self.assertEqual(NjNslp.program_code, "nj_nslp")

    def test_constants(self):
        self.assertEqual(NjNslp.school_days, 180)
        self.assertEqual(NjNslp.max_student_age, 18)
        self.assertEqual(NjNslp.state_lunch_rate, Decimal("0.08"))
        self.assertEqual(NjNslp.state_reduced_price_payment, Decimal("0.40"))
        self.assertEqual(NjNslp.njeie_rate, Decimal("4.31"))

    def test_lunch_rates(self):
        calculator = self.make_calculator(self.household(2, 35))
        student = self.add_member(calculator.screen, "child", 10)
        over_18 = self.add_member(calculator.screen, "child", 19)

        self.assertEqual(calculator.lunch_rate(student, FREE), Decimal("4.84"))
        self.assertEqual(calculator.lunch_rate(student, REDUCED_PRICE), Decimal("4.84"))
        self.assertEqual(calculator.lunch_rate(student, NJEIE), Decimal("4.84"))
        self.assertEqual(calculator.lunch_rate(over_18, FREE), Decimal("4.84"))
        self.assertEqual(calculator.lunch_rate(over_18, REDUCED_PRICE), Decimal("4.44"))

    def test_njeie_limits(self):
        cases = {1: 35_751, 2: 48_474, 4: 73_920, 8: 124_813, 16: 226_599, 17: 239_323}
        for size, limit in cases.items():
            with self.subTest(size=size):
                calculator = self.make_calculator(self.make_screen(household_size=size))
                self.assertEqual(calculator._njeie_limit(), limit)


class TestFederalIncome(NjNslpTestCase):
    def test_scenario_1_parent_and_school_age_child_under_the_federal_limit(self):
        screen = self.household(2, 35, head_wages=30_000)
        self.add_member(screen, "child", 10)

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)

    def test_scenario_2_at_the_federal_reduced_price_limit_child_too_old_for_njeie(self):
        screen = self.household(2, 45, head_wages=40_034)
        self.add_member(screen, "child", 20)

        self.assert_eligible(self.calculate(screen), REDUCED_PRICE_OVER_18_VALUE)

    def test_scenario_3_one_dollar_over_the_federal_limit_child_too_old_for_njeie(self):
        screen = self.household(2, 45, head_wages=40_035)
        self.add_member(screen, "child", 20)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_8_four_person_household_at_the_federal_limit(self):
        screen = self.household(4, 45, head_wages=61_050)
        self.add_member(screen, "spouse", 45)
        self.add_member(screen, "child", 20)
        self.add_member(screen, "child", 20)

        self.assert_eligible(self.calculate(screen), 2 * REDUCED_PRICE_OVER_18_VALUE)

    def test_scenario_9_four_person_household_one_dollar_over_the_federal_limit(self):
        screen = self.household(4, 45, head_wages=61_051)
        self.add_member(screen, "spouse", 45)
        self.add_member(screen, "child", 20)
        self.add_member(screen, "child", 20)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_20_paid_monthly_at_the_federal_monthly_limit(self):
        screen = self.household(2, 45, head_monthly_wages=3_337)
        self.add_member(screen, "child", 20)

        self.assert_eligible(self.calculate(screen), REDUCED_PRICE_OVER_18_VALUE)


class TestNjExpandedIncome(NjNslpTestCase):
    def test_scenario_4_at_the_njeie_limit(self):
        screen = self.household(2, 35, head_wages=48_474)
        self.add_member(screen, "child", 10)

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)

    def test_scenario_5_one_dollar_over_the_njeie_limit(self):
        screen = self.household(2, 35, head_wages=48_475)
        self.add_member(screen, "child", 10)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_6_four_person_household_at_the_njeie_limit(self):
        screen = self.household(4, 40, head_wages=73_920)
        self.add_member(screen, "spouse", 40)
        self.add_member(screen, "child", 12)
        self.add_member(screen, "child", 8)

        self.assert_eligible(self.calculate(screen), 2 * STUDENT_VALUE)

    def test_scenario_7_four_person_household_one_dollar_over_the_njeie_limit(self):
        screen = self.household(4, 40, head_wages=73_921)
        self.add_member(screen, "spouse", 40)
        self.add_member(screen, "child", 12)
        self.add_member(screen, "child", 8)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_19_paid_monthly_at_the_njeie_monthly_limit(self):
        screen = self.household(2, 35, head_monthly_wages=4_040)
        self.add_member(screen, "child", 10)

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)


class TestAge(NjNslpTestCase):
    def test_scenario_10_eighteen_year_old_in_the_njeie_band(self):
        screen = self.household(2, 45, head_wages=45_000)
        self.add_member(screen, "child", 18)

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)

    def test_scenario_11_nineteen_year_old_in_the_njeie_band(self):
        screen = self.household(2, 45, head_wages=45_000)
        self.add_member(screen, "child", 19)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_12_twenty_year_old_under_the_federal_limit(self):
        screen = self.household(2, 50, head_wages=30_000)
        self.add_member(screen, "child", 20)

        self.assert_eligible(self.calculate(screen), REDUCED_PRICE_OVER_18_VALUE)

    def test_scenario_13_twenty_one_year_old_under_the_federal_limit(self):
        screen = self.household(2, 50, head_wages=30_000)
        self.add_member(screen, "child", 21)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_21_twenty_year_old_at_the_federal_free_limit(self):
        screen = self.household(2, 50, head_wages=28_132)
        self.add_member(screen, "child", 20)

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)

    def test_scenario_23_nineteen_year_old_at_the_reduced_price_tier(self):
        screen = self.household(2, 50, head_wages=30_000)
        self.add_member(screen, "child", 19)

        self.assert_eligible(self.calculate(screen), REDUCED_PRICE_OVER_18_VALUE)


class TestCategorical(NjNslpTestCase):
    def test_scenario_14_snap_household_over_every_income_limit(self):
        screen = self.household(2, 35, head_wages=60_000)
        self.add_member(screen, "child", 10)
        self.receive(screen, "snap")

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)

    def test_scenario_15_tanf_household_over_every_income_limit(self):
        screen = self.household(2, 35, head_wages=60_000)
        self.add_member(screen, "child", 10)
        self.receive(screen, "tanf")

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)

    def test_scenario_16_foster_child_and_a_sibling_over_every_income_limit(self):
        screen = self.household(3, 40, head_wages=70_000)
        self.add_member(screen, "fosterChild", 10)
        self.add_member(screen, "child", 8)

        eligibility = self.calculate(screen)

        self.assert_eligible(eligibility, STUDENT_VALUE)
        self.assertEqual([member.value for member in eligibility.eligible_members], [0, STUDENT_VALUE, 0])

    def test_scenario_17_head_start_household_over_every_income_limit(self):
        screen = self.household(3, 30, head_wages=70_000)
        self.add_member(screen, "child", 4)
        self.add_member(screen, "child", 8)
        self.receive(screen, "head_start")

        self.assert_eligible(self.calculate(screen), 2 * STUDENT_VALUE)

    def test_scenario_18_wic_household_over_every_income_limit(self):
        screen = self.household(2, 30, head_wages=60_000)
        self.add_member(screen, "child", 10)
        self.receive(screen, "wic")

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_22_twenty_year_old_in_a_snap_household_above_the_free_limit(self):
        screen = self.household(2, 50, head_wages=35_000)
        self.add_member(screen, "child", 20)
        self.receive(screen, "snap")

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)


class TestWithoutSnapOrTanfPrograms(NjNslpTestCase):
    """NJ has no SNAP or TANF program yet. The categorical routes read the household's own
    reported benefits, never those programs' rows or results, so their absence must not stop
    the calculation."""

    def test_calculates_when_no_snap_or_tanf_program_exists(self):
        self.assertFalse(Program.objects.filter(base_program__in=["snap", "tanf"]).exists())
        screen = self.household(2, 35, head_wages=30_000)
        self.add_member(screen, "child", 10)

        self.assert_eligible(self.calculate(screen), STUDENT_VALUE)
