"""
Unit tests for the NSLP MFB base (``NationalSchoolLunchProgram``).

Exercised through a test-only state. The base spec has no scenarios of its own, so each rule in
its sections 3, 4 and 7 gets a test here; NJ's spec scenarios run end to end in ``test_nj.py``.
"""

from decimal import Decimal

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility
from programs.framework.pe_dependencies.receipt import TANF_INCOME_TYPE
from programs.programs.cross_white_label.nslp.mfb_base import FREE, REDUCED_PRICE, NationalSchoolLunchProgram
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.util import DependencyError
from screener.models import Screen
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

# 2026 poverty guideline for 2 is 21,640: free ceil(1.30 x) = 28,132, reduced ceil(1.85 x) = 40,034.
FREE_LIMIT_2 = 28_132
REDUCED_PRICE_LIMIT_2 = 40_034

# (0.45 + 4.31) x 180 and (0.45 + 3.91) x 180, rounded to whole dollars.
FREE_VALUE = 857
REDUCED_PRICE_VALUE = 785


class StateNslp(NationalSchoolLunchProgram):
    program_code = "test_nslp"
    school_days = 180


class NslpBaseTestCase(CustomCalculatorTestCase):
    calculator_class = StateNslp
    fpl_year = "2026"

    def household(self, size: int = 2, head_wages: int = 0) -> Screen:
        screen = self.make_screen(household_size=size)
        self.add_member(screen, "headOfHousehold", 35, yearly_income=head_wages)

        return screen

    def receive(self, screen: Screen, base_program: str) -> None:
        name = f"test_{base_program}_stand_in"
        seed_program(self.white_label, name, base_program=base_program)
        _write_current_benefits(screen, [name])
        screen.invalidate_current_benefits_cache()

    def member_values(self, eligibility: Eligibility) -> list[int]:
        return [member.value for member in eligibility.eligible_members]


class TestDeclarations(NslpBaseTestCase):
    def test_base_is_abstract(self):
        self.assertTrue(NationalSchoolLunchProgram._abstract)
        self.assertFalse(hasattr(NationalSchoolLunchProgram, "program_code"))

    def test_constants(self):
        self.assertEqual(NationalSchoolLunchProgram.max_age, 20)
        self.assertEqual(NationalSchoolLunchProgram.free_percent, 130)
        self.assertEqual(NationalSchoolLunchProgram.reduced_price_percent, 185)
        self.assertEqual(NationalSchoolLunchProgram.section_4_rate, Decimal("0.45"))
        self.assertEqual(
            NationalSchoolLunchProgram.section_11_rates, {FREE: Decimal("4.31"), REDUCED_PRICE: Decimal("3.91")}
        )

    def test_missing_income_drops_the_program(self):
        screen = self.household()
        self.add_member(screen, "child", 10)

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=("income_amount",))


class TestSchoolChild(NslpBaseTestCase):
    def test_twenty_year_old_is_a_school_child(self):
        screen = self.household()
        self.add_member(screen, "child", 20)

        self.assertTrue(self.calculate(screen).eligible)

    def test_twenty_one_year_old_is_not(self):
        screen = self.household()
        self.add_member(screen, "child", 21)

        eligibility = self.calculate(screen)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_no_lower_age_bound(self):
        screen = self.household()
        self.add_member(screen, "child", 0)

        self.assertEqual(self.member_values(self.calculate(screen)), [0, FREE_VALUE])

    def test_no_relationship_test(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 19)

        self.assertEqual(self.member_values(self.calculate(screen)), [FREE_VALUE])


class TestIncome(NslpBaseTestCase):
    def test_at_the_free_limit_is_free(self):
        screen = self.household(head_wages=FREE_LIMIT_2)
        self.add_member(screen, "child", 10)

        eligibility = self.calculate(screen)

        self.assertEqual(self.member_values(eligibility), [0, FREE_VALUE])
        self.assertEqual(eligibility.pass_messages, [messages.income(FREE_LIMIT_2, REDUCED_PRICE_LIMIT_2)])

    def test_one_dollar_over_the_free_limit_is_reduced_price(self):
        screen = self.household(head_wages=FREE_LIMIT_2 + 1)
        self.add_member(screen, "child", 10)

        self.assertEqual(self.member_values(self.calculate(screen)), [0, REDUCED_PRICE_VALUE])

    def test_at_the_reduced_price_limit(self):
        screen = self.household(head_wages=REDUCED_PRICE_LIMIT_2)
        self.add_member(screen, "child", 10)

        self.assertEqual(self.member_values(self.calculate(screen)), [0, REDUCED_PRICE_VALUE])

    def test_one_dollar_over_the_reduced_price_limit(self):
        screen = self.household(head_wages=REDUCED_PRICE_LIMIT_2 + 1)
        self.add_member(screen, "child", 10)

        eligibility = self.calculate(screen)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)
        self.assertEqual(eligibility.fail_messages, [messages.income(REDUCED_PRICE_LIMIT_2 + 1, REDUCED_PRICE_LIMIT_2)])

    def test_limit_follows_household_size(self):
        # 2026 guideline for 4 is 33,000: reduced ceil(1.85 x) = 61,050.
        screen = self.household(size=4, head_wages=61_050)
        self.add_member(screen, "spouse", 40)
        self.add_member(screen, "child", 10)
        self.add_member(screen, "child", 12)
        self.assertTrue(self.calculate(screen).eligible)

        over = self.household(size=4, head_wages=61_051)
        self.add_member(over, "spouse", 40)
        self.add_member(over, "child", 10)
        self.add_member(over, "child", 12)
        self.assertFalse(self.calculate(over).eligible)


class TestIncomeFrequency(NslpBaseTestCase):
    """Same-frequency income is tested at that frequency's limit, the annual limit divided down and rounded up."""

    def household_paid(self, amount: int, frequency: str) -> Screen:
        screen = self.household()
        self.add_income(screen.household_members.get(), amount, frequency=frequency)
        self.add_member(screen, "child", 10)

        return screen

    def test_monthly_at_the_monthly_limit(self):
        # ceil(40,034 / 12) = 3,337; twelve of them is 40,044, over the annual limit.
        self.assertTrue(self.calculate(self.household_paid(3_337, "monthly")).eligible)
        self.assertFalse(self.calculate(self.household_paid(3_338, "monthly")).eligible)

    def test_semimonthly_at_its_limit(self):
        # ceil(40,034 / 24) = 1,669
        self.assertTrue(self.calculate(self.household_paid(1_669, "semimonthly")).eligible)
        self.assertFalse(self.calculate(self.household_paid(1_670, "semimonthly")).eligible)

    def test_biweekly_at_its_limit(self):
        # ceil(40,034 / 26) = 1,540
        self.assertTrue(self.calculate(self.household_paid(1_540, "biweekly")).eligible)
        self.assertFalse(self.calculate(self.household_paid(1_541, "biweekly")).eligible)

    def test_weekly_at_its_limit(self):
        # ceil(40,034 / 52) = 770
        self.assertTrue(self.calculate(self.household_paid(770, "weekly")).eligible)
        self.assertFalse(self.calculate(self.household_paid(771, "weekly")).eligible)

    def test_free_tier_also_compares_at_the_reported_frequency(self):
        # ceil(28,132 / 12) = 2,345; twelve of them is 28,140, over the annual free limit.
        screen = self.household_paid(2_345, "monthly")

        self.assertEqual(self.member_values(self.calculate(screen)), [0, FREE_VALUE])

    def test_mixed_frequencies_are_annualized(self):
        # 3,000 a month and 4,100 a year is 40,100 a year, over 40,034, though each stream alone is under.
        screen = self.household()
        head = screen.household_members.get()
        self.add_income(head, 3_000, frequency="monthly")
        self.add_income(head, 4_100, frequency="yearly")
        self.add_member(screen, "child", 10)

        self.assertFalse(self.calculate(screen).eligible)


class TestCategorical(NslpBaseTestCase):
    def assert_every_child_free(self, screen: Screen) -> None:
        eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(self.member_values(eligibility), [0, FREE_VALUE, FREE_VALUE])
        self.assertEqual(eligibility.pass_messages, [messages.presumed_eligibility()])

    def over_income_household(self) -> Screen:
        screen = self.household(size=3, head_wages=200_000)
        self.add_member(screen, "child", 4)
        self.add_member(screen, "child", 20)

        return screen

    def test_snap_makes_every_child_free(self):
        screen = self.over_income_household()
        self.receive(screen, "snap")

        self.assert_every_child_free(screen)

    def test_tanf_makes_every_child_free(self):
        screen = self.over_income_household()
        self.receive(screen, "tanf")

        self.assert_every_child_free(screen)

    def test_reported_tanf_income_makes_every_child_free(self):
        screen = self.over_income_household()
        self.add_income(screen.household_members.first(), 300, income_type=TANF_INCOME_TYPE)

        self.assert_every_child_free(screen)

    def test_head_start_makes_every_child_free(self):
        screen = self.over_income_household()
        self.receive(screen, "head_start")

        self.assert_every_child_free(screen)

    def test_a_benefit_outside_the_categories_does_not(self):
        screen = self.over_income_household()
        self.receive(screen, "wic")

        self.assertFalse(self.calculate(screen).eligible)

    def test_foster_child_is_free_and_their_sibling_is_not(self):
        screen = self.household(size=3, head_wages=200_000)
        self.add_member(screen, "fosterChild", 10)
        self.add_member(screen, "child", 8)

        eligibility = self.calculate(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(self.member_values(eligibility), [0, FREE_VALUE, 0])
        self.assertEqual(eligibility.pass_messages, [])

    def test_foster_child_over_twenty_does_not_qualify(self):
        screen = self.household(size=2, head_wages=200_000)
        self.add_member(screen, "fosterChild", 21)

        self.assertFalse(self.calculate(screen).eligible)
