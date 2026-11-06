"""
Housing Choice Voucher base (``HousingChoiceVoucher``), through test-only subclasses that set
the values a state sets. The base spec has no scenarios of its own, so each base rule its
sections 4 and 7 state gets a test here; NJ's scenarios run end to end in ``test_nj.py``.

HUD figures are round stand-ins: a $50,000 limit and a $1,000 payment standard, so each value
reads as $1,000 less the tenant payment.
"""

from decimal import Decimal
from unittest.mock import patch

import programs.framework.eligibility_messages as messages
from programs.programs.cross_white_label.hcv.base import HousingChoiceVoucher
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase, hud_ami
from programs.framework.base import Eligibility
from screener.models import HouseholdMember, Screen

LIMIT = 50_000
PAYMENT_STANDARD = 1_000


class StateHcv(HousingChoiceVoucher):
    program_code = "test_hcv"
    net_assets_limit_amount = 100_000
    student_earnings_cap = 480
    dependent_deduction = 480
    elderly_disabled_deduction = 525
    minimum_rent = 0
    special_category_assumed = False
    payment_standard_year = 2027
    subsidy_standards = ((0, 1, 1), (1, 2, 2), (2, 3, 4), (3, 5, 6), (4, 7, 8))


class MinimumRentStateHcv(StateHcv):
    program_code = "test_hcv_minimum_rent"
    minimum_rent = 50


class AdditionalDeductionStateHcv(StateHcv):
    program_code = "test_hcv_additional_deduction"

    def additional_deductions(self) -> Decimal:
        return Decimal(4_000)


class LargeUnitStateHcv(StateHcv):
    program_code = "test_hcv_large_unit"
    subsidy_standards = ((6, 1, 8),)


class HcvBaseTestCase(CustomCalculatorTestCase):
    calculator_class = StateHcv
    fpl_year = "2026"
    default_zipcode = "00000"
    default_county = "Test County"
    stores_age = False

    def run_screen(
        self, screen: Screen, limit: int = LIMIT, payment_standard: int = PAYMENT_STANDARD, **hud_kwargs
    ) -> Eligibility:
        with hud_ami(HousingChoiceVoucher, {"50%": limit, "80%": limit}, payment_standard, **hud_kwargs) as hud:
            e = self.calculate(screen)
        self.hud = hud
        return e

    def ttp(self, screen: Screen) -> int:
        """The tenant payment, read back from the value."""
        e = self.run_screen(screen)
        self.assertTrue(e.eligible)
        return PAYMENT_STANDARD - e.value // 12

    def household(self, size: int = 1, assets: int = 0) -> Screen:
        return self.make_screen(household_size=size, household_assets=assets)


class TestIncomeLimitRoute(HcvBaseTestCase):
    def test_very_low_income_limit_without_special_category(self) -> None:
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40, yearly_income=LIMIT)
        self.assertTrue(self.run_screen(screen).eligible)
        self.hud.get_screen_il_ami.assert_called_once_with(screen, "50%", "2026")

    def test_one_dollar_over_the_limit(self) -> None:
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40, yearly_income=LIMIT + 1)
        e = self.run_screen(screen)
        self.assertFalse(e.eligible)
        self.assertIn(messages.income(LIMIT + 1, LIMIT), e.fail_messages)

    def test_special_category_route_reads_the_low_income_row(self) -> None:
        class SpecialCategoryStateHcv(StateHcv):
            program_code = "test_hcv_special_category"
            special_category_assumed = True

        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40)
        calculator = SpecialCategoryStateHcv(screen, self.program, {}, None)
        self.assertEqual(calculator.income_limit_percent(), "80%")

    def test_hud_unavailable_is_not_eligible(self) -> None:
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40)
        e = self.run_screen(screen, unavailable=True)
        self.assertFalse(e.eligible)
        self.assertIn(messages.income_limit_unknown(), e.fail_messages)

    def test_unexpected_lookup_failure_is_not_eligible(self) -> None:
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40)
        with hud_ami(HousingChoiceVoucher, payment_standard=PAYMENT_STANDARD) as hud:
            hud.get_screen_il_ami.side_effect = ValueError("bad payload")
            e = self.calculate(screen)
        self.assertFalse(e.eligible)

    def test_missing_program_year_is_not_eligible(self) -> None:
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40)
        self.program.year = None
        self.addCleanup(setattr, self.program, "year", self.program_year)
        e = self.run_screen(screen)
        self.assertFalse(e.eligible)
        self.assertIn(messages.income_limit_unknown(), e.fail_messages)


class TestAnnualIncome(HcvBaseTestCase):
    def annual_income(self, screen: Screen) -> int:
        return int(self.make_calculator(screen).annual_income())

    def test_workers_compensation_does_not_count(self) -> None:
        screen = self.household()
        head = self.add_member(screen, "headOfHousehold", 40, yearly_income=10_000)
        self.add_income(head, 5_000, "workersComp", "yearly")
        self.assertEqual(self.annual_income(screen), 10_000)

    def test_minor_unearned_income_counts_and_earnings_do_not(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 40, yearly_income=10_000)
        child = self.add_member(screen, "child", 16, yearly_income=3_000)
        self.add_income(child, 1_200, "sSI", "yearly")
        self.assertEqual(self.annual_income(screen), 11_200)

    def test_spouse_under_18_earnings_count(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 19, yearly_income=10_000)
        self.add_member(screen, "spouse", 17, yearly_income=4_000)
        self.assertEqual(self.annual_income(screen), 14_000)

    def test_domestic_partner_under_18_is_not_a_spouse(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 19, yearly_income=10_000)
        self.add_member(screen, "domesticPartner", 17, yearly_income=4_000)
        self.assertEqual(self.annual_income(screen), 10_000)

    def test_student_cap_applies_to_a_dependent_not_the_spouse(self) -> None:
        screen = self.household(3)
        self.add_member(screen, "headOfHousehold", 45, yearly_income=10_000)
        self.add_member(screen, "spouse", 22, yearly_income=6_000, student=True, student_full_time=True)
        self.add_member(screen, "child", 19, yearly_income=6_000, student=True, student_full_time=True)
        self.assertEqual(self.annual_income(screen), 10_000 + 6_000 + 480)

    def test_student_cap_leaves_unearned_income_whole(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 45)
        child = self.add_member(screen, "child", 19, yearly_income=6_000, student=True, student_full_time=True)
        self.add_income(child, 2_000, "childSupport", "yearly")
        self.assertEqual(self.annual_income(screen), 480 + 2_000)

    def test_unknown_age_counts_in_full(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 45)
        roommate = self.add_member(screen, "roommate", 30, yearly_income=7_000)
        self.set_age(roommate, None)
        self.assertEqual(self.annual_income(screen), 7_000)


class TestAssets(HcvBaseTestCase):
    def test_assets_at_limit(self) -> None:
        screen = self.household(assets=100_000)
        self.add_member(screen, "headOfHousehold", 40)
        self.assertTrue(self.run_screen(screen).eligible)

    def test_assets_over_limit(self) -> None:
        screen = self.household(assets=100_001)
        self.add_member(screen, "headOfHousehold", 40)
        e = self.run_screen(screen)
        self.assertFalse(e.eligible)
        self.assertIn(messages.assets(100_000), e.fail_messages)

    def test_blank_assets_read_as_zero(self) -> None:
        screen = self.household(assets=None)
        self.add_member(screen, "headOfHousehold", 40)
        self.assertTrue(self.run_screen(screen).eligible)


class TestStudentBar(HcvBaseTestCase):
    def student(self, screen: Screen, relationship: str, age: int = 20) -> HouseholdMember:
        return self.add_member(screen, relationship, age, student=True, student_full_time=True)

    def test_roommate_student_bars_the_household(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 40)
        self.student(screen, "roommate")
        self.assertFalse(self.run_screen(screen).eligible)

    def test_grandchild_student_is_barred(self) -> None:
        # Relationships run to the head, so a grandchild can't be linked to their own parent.
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 60)
        self.student(screen, "grandChild")
        self.assertFalse(self.run_screen(screen).eligible)

    def test_head_living_with_a_parent_is_not_barred(self) -> None:
        screen = self.household(2)
        self.student(screen, "headOfHousehold")
        self.add_member(screen, "parent", 50)
        self.assertTrue(self.run_screen(screen).eligible)

    def test_head_with_a_stepchild_is_not_barred(self) -> None:
        screen = self.household(2)
        self.student(screen, "headOfHousehold", 22)
        self.add_member(screen, "stepChild", 4)
        self.assertTrue(self.run_screen(screen).eligible)

    def test_spouse_student_is_married(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 25)
        self.student(screen, "spouse", 21)
        self.assertTrue(self.run_screen(screen).eligible)

    def test_spouse_student_with_the_heads_child_has_a_child(self) -> None:
        # The spouse is married anyway; this checks the has-child link reaches the spouse.
        screen = self.household(3)
        self.add_member(screen, "headOfHousehold", 25)
        spouse = self.student(screen, "spouse", 21)
        self.add_member(screen, "child", 2)
        members = list(screen.household_members.all())
        calculator = self.make_calculator(screen)
        self.assertFalse(calculator._is_barred_student(spouse, members))

    def test_head_with_a_domestic_partner_is_not_married(self) -> None:
        screen = self.household(2)
        self.student(screen, "headOfHousehold", 21)
        self.add_member(screen, "domesticPartner", 22)
        self.assertFalse(self.run_screen(screen).eligible)

    def test_blank_full_time_answer_is_not_barred(self) -> None:
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 20, student=True, student_full_time=None)
        self.assertTrue(self.run_screen(screen).eligible)

    def test_student_of_unknown_age_is_not_barred(self) -> None:
        screen = self.household()
        head = self.student(screen, "headOfHousehold")
        self.set_age(head, None)
        self.assertTrue(self.run_screen(screen).eligible)


class TestTenantPayment(HcvBaseTestCase):
    def test_foster_child_is_not_a_dependent(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 40)
        self.add_member(screen, "fosterChild", 8)
        self.assertEqual(self.make_calculator(screen).dependents(), 0)

    def test_adult_with_a_disability_is_a_dependent(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 60)
        self.add_member(screen, "child", 30, disabled=True)
        self.assertEqual(self.make_calculator(screen).dependents(), 1)

    def test_young_domestic_partner_is_a_dependent(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 19)
        self.add_member(screen, "domesticPartner", 17)
        self.assertEqual(self.make_calculator(screen).dependents(), 1)

    def test_elderly_spouse_makes_an_elderly_family(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 50)
        self.add_member(screen, "spouse", 62)
        self.assertTrue(self.make_calculator(screen).is_elderly_or_disabled_family())

    def test_elderly_parent_does_not(self) -> None:
        screen = self.household(2)
        self.add_member(screen, "headOfHousehold", 50)
        self.add_member(screen, "parent", 80)
        self.assertFalse(self.make_calculator(screen).is_elderly_or_disabled_family())

    def test_dependent_care_is_not_child_care(self) -> None:
        # round(30% × $12,000 ÷ 12) = $300, with no deduction for dependent care.
        screen = self.household(2)
        head = self.add_member(screen, "headOfHousehold", 40, yearly_income=12_480)
        self.add_member(screen, "child", 5)
        self.add_expense(head, 300, "dependentCare")
        self.assertEqual(self.ttp(screen), 300)

    def test_ten_percent_of_gross_income_floor(self) -> None:
        # Adjusted income is $0 after child care, so 10% of $12,000 ÷ 12 = $100.
        screen = self.household(2)
        head = self.add_member(screen, "headOfHousehold", 40, yearly_income=12_000)
        self.add_member(screen, "child", 5)
        self.add_expense(head, 20_000, "childCare", "yearly")
        self.assertEqual(self.ttp(screen), 100)

    def test_rounds_an_exact_half_up(self) -> None:
        # 30% × $20,020 ÷ 12 = $500.50, which rounds up to $501.
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40, yearly_income=20_020)
        self.assertEqual(self.ttp(screen), 501)

    def test_minimum_rent(self) -> None:
        self.calculator_class = MinimumRentStateHcv
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40)
        self.assertEqual(self.ttp(screen), 50)

    def test_additional_deductions(self) -> None:
        # round(30% × ($12,000 − $4,000) ÷ 12) = $200
        self.calculator_class = AdditionalDeductionStateHcv
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40, yearly_income=12_000)
        self.assertEqual(self.ttp(screen), 200)


class TestPaymentStandard(HcvBaseTestCase):
    def test_reads_the_states_fmr_year_and_voucher_size(self) -> None:
        screen = self.household(3)
        self.add_member(screen, "headOfHousehold", 40)
        e = self.run_screen(screen)
        self.assertEqual(e.value, PAYMENT_STANDARD * 12)
        self.hud.get_screen_payment_standard.assert_called_once_with(screen, 2, 2027)

    def test_bedrooms_past_four_add_fifteen_percent_each(self) -> None:
        # Six bedrooms: the four-bedroom $1,000 × (1 + 2 × 15%) = $1,300.
        self.calculator_class = LargeUnitStateHcv
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40)
        e = self.run_screen(screen)
        self.assertEqual(e.value, 1_300 * 12)
        self.hud.get_screen_payment_standard.assert_called_once_with(screen, 4, 2027)

    def test_no_voucher_size_is_valued_at_zero(self) -> None:
        screen = self.household(9)
        self.add_member(screen, "headOfHousehold", 40)
        e = self.run_screen(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_unavailable_is_valued_at_zero(self) -> None:
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40)
        e = self.run_screen(screen, payment_standard_unavailable=True)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_unexpected_value_failure_is_valued_at_zero(self) -> None:
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40)
        with patch.object(StateHcv, "total_tenant_payment", side_effect=ValueError("bug")):
            e = self.run_screen(screen)
        self.assertEqual(e.value, 0)

    def test_payment_at_or_below_zero_is_floored_at_one_dollar(self) -> None:
        # round(30% × $48,000 ÷ 12) = $1,200 is more than the $1,000 standard.
        screen = self.household()
        self.add_member(screen, "headOfHousehold", 40, yearly_income=48_000)
        e = self.run_screen(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1)


class TestDependencies(HcvBaseTestCase):
    def test_declares_the_fields_it_reads(self) -> None:
        self.assertEqual(
            set(StateHcv.dependencies),
            {
                "income_type",
                "income_amount",
                "income_frequency",
                "household_size",
                "household_assets",
                "county",
                "zipcode",
                "age",
                "relationship",
            },
        )

    def test_not_calculated_without_a_county(self) -> None:
        screen = self.household()
        self.assertFalse(self.make_calculator(screen, missing=("county",)).can_calc())
