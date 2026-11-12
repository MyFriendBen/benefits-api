"""
The SNAP MFB federal base (``MfbSnap``), tested through stand-in states that set what a state
sets. The base spec (``programs/cross_white_label/snap/base/snap_base_spec.md`` in program-ops)
has no scenarios of its own; each state's run end to end in its own test file.

Dollar figures are monthly unless a test says "value", which is annual.
"""

from decimal import Decimal
from typing import Optional
from unittest.mock import patch

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.snap import mfb_base
from programs.programs.cross_white_label.snap.mfb_base import MfbSnap
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import Screen


class StandInSnap(MfbSnap, abstract=True):
    """A state that sets nothing: actual utility bills count and only the federal rules apply."""


class StandInSnapWithAllowance(MfbSnap, abstract=True):
    """A state that requires its 400 dollar standard utility allowance."""

    utility_allowance = 400


class StandInSnapWithExtraRoute(MfbSnap, abstract=True):
    """A state that also passes a household reporting 'general assistance' income."""

    def categorically_eligible(self) -> bool:
        return super().categorically_eligible() or self.screen.calc_gross_income("yearly", ["generalAssistance"]) > 0


def reports_tanf_tile(base_program: str) -> bool:
    return base_program == "tanf"


class MfbSnapTestCase(CustomCalculatorTestCase):
    calculator_class = StandInSnap
    needs_program_row = False
    stores_age = False

    def household(self, *people: tuple, size: Optional[int] = None, assets: int = 0) -> Screen:
        """A screen from (relationship, age[, member kwargs]) tuples; size defaults to the people listed."""
        screen = self.make_screen(household_size=size or len(people), household_assets=assets)
        for person in people:
            relationship, age, *rest = person
            self.add_member(screen, relationship, age, **(rest[0] if rest else {}))

        return screen

    def single(self, age: int = 40, assets: int = 0, **member_kwargs) -> Screen:
        return self.household(("headOfHousehold", age, member_kwargs), assets=assets)

    def head_of(self, screen: Screen):
        return screen.household_members.get(relationship="headOfHousehold")

    def expense(self, screen: Screen, amount: int, expense_type: str) -> None:
        self.add_expense(self.head_of(screen), amount, expense_type)

    def calculator(self, screen: Screen, calculator_class: Optional[type] = None) -> MfbSnap:
        original = self.calculator_class
        try:
            if calculator_class is not None:
                self.calculator_class = calculator_class
            return self.make_calculator(screen)
        finally:
            self.calculator_class = original

    def assert_eligible(self, eligibility: Eligibility, value: int) -> None:
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, value)

    def assert_ineligible(self, eligibility: Eligibility) -> None:
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)


class TestFederalFigures(MfbSnapTestCase):
    def test_gross_limits_by_size(self):
        self.assertEqual([mfb_base.gross_income_limit(n) for n in (1, 4, 8)], [1729, 3575, 6037])

    def test_gross_limit_adds_per_member_above_eight(self):
        self.assertEqual(mfb_base.gross_income_limit(9), 6037 + 616)
        self.assertEqual(mfb_base.gross_income_limit(10), 6037 + 2 * 616)

    def test_net_limits_by_size(self):
        self.assertEqual([mfb_base.net_income_limit(n) for n in (1, 4, 8)], [1330, 2750, 4644])
        self.assertEqual(mfb_base.net_income_limit(10), 4644 + 2 * 474)

    def test_max_allotments_by_size(self):
        self.assertEqual([mfb_base.max_allotment(n) for n in (1, 2, 3, 8)], [306, 562, 808, 1841])

    def test_max_allotment_adds_225_from_nine_to_seventeen(self):
        self.assertEqual(mfb_base.max_allotment(9), 1841 + 225)
        self.assertEqual(mfb_base.max_allotment(17), 1841 + 225 * 9)

    def test_max_allotment_is_flat_from_eighteen(self):
        self.assertEqual(mfb_base.max_allotment(18), 3887)
        self.assertEqual(mfb_base.max_allotment(25), 3887)

    def test_standard_deduction_is_the_minimum_until_eight_point_three_one_percent_passes_it(self):
        # 8.31% of 2,750 is 228.5, rounded up to 229; of 3,224 is 267.9 -> 268; of 3,697 is 307.2 -> 308.
        self.assertEqual([mfb_base.standard_deduction(n) for n in (1, 2, 3)], [217, 217, 217])
        self.assertEqual([mfb_base.standard_deduction(n) for n in (4, 5, 6)], [229, 268, 308])

    def test_standard_deduction_stops_growing_after_size_six(self):
        self.assertEqual(mfb_base.standard_deduction(9), 308)


class TestIncomeTests(MfbSnapTestCase):
    def test_single_earner_gets_the_allotment_after_deductions(self):
        # 1,000 - 200 (20% of earnings) - 217 = 583; 30% rounds up to 175; 306 - 175 = 131.
        screen = self.single(monthly_income=1_000)

        self.assert_eligible(self.calculate(screen), 131 * 12)

    def test_gross_income_at_the_limit_passes(self):
        screen = self.single(monthly_income=1_729)

        self.assertTrue(self.calculate(screen).eligible)

    def test_gross_income_one_dollar_over_the_limit_fails(self):
        screen = self.single(monthly_income=1_730)

        self.assert_ineligible(self.calculate(screen))

    def test_net_income_at_the_limit_passes(self):
        # Unearned, so no 20% deduction: 1,547 - 217 = 1,330, the net limit for one person.
        screen = self.single(monthly_income=1_547, income_type="unemployment")

        calculator = self.calculator(screen)
        self.assertEqual(calculator.net_income, 1_330)
        self.assert_eligible(self.calculate(screen), 25 * 12)

    def test_net_income_one_dollar_over_the_limit_fails(self):
        screen = self.single(monthly_income=1_548, income_type="unemployment")

        self.assert_ineligible(self.calculate(screen))

    def test_minimum_benefit_applies_to_one_and_two_person_households(self):
        # 30% of 1,330 is 399, above the 306 maximum, so the 25 dollar minimum is the allotment.
        screen = self.single(monthly_income=1_547, income_type="unemployment")

        self.assertEqual(self.calculator(screen).allotment(), 25)

    def test_dependent_care_comes_off_net_income(self):
        # 1,500 - 300 - 217 - (300 child care + 100 dependent care) = 583; 562 - 175 = 387.
        screen = self.household(
            ("headOfHousehold", 30, {"monthly_income": 1_500}),
            ("child", 5),
        )
        self.expense(screen, 300, "childCare")
        self.expense(screen, 100, "dependentCare")

        self.assertEqual(self.calculator(screen).net_income, 583)
        self.assert_eligible(self.calculate(screen), 387 * 12)

    def test_child_support_paid_comes_off_countable_income(self):
        # 1,800 is over the 1,729 gross limit, but 1,800 - 100 child support is 1,700.
        screen = self.single(monthly_income=1_800, income_type="unemployment")
        self.expense(screen, 100, "childSupport")
        self.expense(screen, 1_000, "rent")

        self.assertEqual(self.calculator(screen).countable_income, 1_700)
        self.assertTrue(self.calculate(screen).eligible)

    def test_same_income_without_child_support_fails_the_gross_test(self):
        screen = self.single(monthly_income=1_800, income_type="unemployment")
        self.expense(screen, 1_000, "rent")

        self.assert_ineligible(self.calculate(screen))

    def test_self_employment_and_boarder_income_get_the_earned_deduction(self):
        for income_type in ("selfEmployment", "boarder"):
            with self.subTest(income_type):
                screen = self.single(monthly_income=1_000, income_type=income_type)

                self.assertEqual(self.calculator(screen).net_income, 583)

    def test_unearned_income_gets_no_earned_deduction(self):
        screen = self.single(monthly_income=1_000, income_type="pension")

        self.assertEqual(self.calculator(screen).net_income, 783)

    def test_no_income_gets_the_maximum(self):
        screen = self.single()

        self.assert_eligible(self.calculate(screen), 306 * 12)

    def test_net_income_never_goes_below_zero(self):
        screen = self.single(monthly_income=100)

        self.assertEqual(self.calculator(screen).net_income, 0)


class TestShelterAndMedicalDeductions(MfbSnapTestCase):
    def test_rent_over_half_of_remaining_income_is_deducted(self):
        # 1,700 - 217 = 1,483; half is 741.5; rent 1,000 leaves 258.5 excess; net 1,224.5.
        screen = self.single(monthly_income=1_700, income_type="unemployment")
        self.expense(screen, 1_000, "rent")

        self.assertEqual(self.calculator(screen).net_income, Decimal("1224.5"))
        self.assert_eligible(self.calculate(screen), 25 * 12)

    def test_every_shelter_cost_counts(self):
        # 1,000 income - 217 = 783, half is 391.5; each of these is 100, total 500 + utilities 200.
        screen = self.single(monthly_income=1_000, income_type="pension")
        for expense_type in ("rent", "mortgage", "propertyTax", "hoa", "homeownersInsurance"):
            self.expense(screen, 100, expense_type)
        for expense_type in ("heating", "cooling"):
            self.expense(screen, 100, expense_type)

        # shelter 700 - 391.5 = 308.5 excess; net 783 - 308.5 = 474.5
        self.assertEqual(self.calculator(screen).net_income, Decimal("474.5"))

    def test_telephone_and_other_utilities_count_as_utilities(self):
        screen = self.single(monthly_income=1_000, income_type="pension")
        self.expense(screen, 200, "telephone")
        self.expense(screen, 200, "otherUtilities")

        # shelter 400 - 391.5 = 8.5 excess; net 783 - 8.5
        self.assertEqual(self.calculator(screen).net_income, Decimal("774.5"))

    def test_internet_is_not_a_shelter_cost(self):
        screen = self.single(monthly_income=1_000, income_type="pension")
        self.expense(screen, 600, "rent")
        net_without_internet = self.calculator(screen).net_income

        self.expense(screen, 100, "internet")

        self.assertEqual(self.calculator(self.refreshed(screen)).net_income, net_without_internet)

    def test_shelter_deduction_is_capped_for_a_household_with_no_elderly_or_disabled_member(self):
        # 1,500 - 217 = 1,283; half is 641.5; rent 2,000 leaves 1,358.5 excess, capped at 769.
        # Net 514; 30% rounds up to 155; 306 - 155 = 151.
        screen = self.single(monthly_income=1_500, income_type="unemployment")
        self.expense(screen, 2_000, "rent")

        self.assertEqual(self.calculator(screen).net_income, 514)
        self.assert_eligible(self.calculate(screen), 151 * 12)

    def test_shelter_deduction_is_uncapped_with_an_elderly_member(self):
        screen = self.single(age=65, monthly_income=1_500, income_type="pension")
        self.expense(screen, 2_000, "rent")

        self.assertEqual(self.calculator(screen).net_income, 0)
        self.assert_eligible(self.calculate(screen), 306 * 12)

    def test_shelter_deduction_is_uncapped_with_a_disabled_member(self):
        screen = self.single(monthly_income=1_500, income_type="unemployment", disabled=True)
        self.expense(screen, 2_000, "rent")

        self.assertEqual(self.calculator(screen).net_income, 0)

    def test_shelter_is_the_state_allowance_in_place_of_actual_utilities(self):
        # 1,000 - 217 = 783; half 391.5; shelter 600 rent + 400 allowance = 1,000; net 783 - 608.5.
        screen = self.single(monthly_income=1_000, income_type="unemployment")
        self.expense(screen, 600, "rent")
        self.expense(screen, 50, "heating")

        self.assertEqual(self.calculator(screen, StandInSnapWithAllowance).net_income, Decimal("174.5"))

    def test_actual_utilities_count_when_the_state_sets_no_allowance(self):
        screen = self.single(monthly_income=1_000, income_type="unemployment")
        self.expense(screen, 600, "rent")
        self.expense(screen, 50, "heating")

        # shelter 650 - 391.5 = 258.5 excess; net 524.5
        self.assertEqual(self.calculator(screen).net_income, Decimal("524.5"))

    def test_medical_costs_over_35_are_deducted_for_an_elderly_member(self):
        # 1,400 - 217 - (135 - 35) = 1,083.
        screen = self.single(age=65, monthly_income=1_400, income_type="pension")
        self.expense(screen, 135, "medical")

        self.assertEqual(self.calculator(screen).net_income, 1_083)

    def test_medical_costs_are_deducted_for_a_member_reporting_ssdi(self):
        screen = self.single(age=40)
        self.add_income(self.head_of(screen), 1_400, "sSDisability")
        self.expense(screen, 135, "medical")

        self.assertEqual(self.calculator(screen).net_income, 1_083)

    def test_medical_costs_are_not_deducted_without_an_elderly_or_disabled_member(self):
        screen = self.single(age=40, monthly_income=1_400, income_type="unemployment")
        self.expense(screen, 135, "medical")

        self.assertEqual(self.calculator(screen).net_income, 1_183)

    def test_medical_costs_under_35_deduct_nothing(self):
        screen = self.single(age=65, monthly_income=1_400, income_type="pension")
        self.expense(screen, 30, "medical")

        self.assertEqual(self.calculator(screen).net_income, 1_183)

    def refreshed(self, screen: Screen) -> Screen:
        return Screen.objects.get(pk=screen.pk)


class TestElderlyOrDisabled(MfbSnapTestCase):
    def test_gross_test_is_skipped_for_a_member_60_or_older(self):
        # 2,000 gross is over 1,729; rent brings net to 1,174.5.
        screen = self.single(age=60, monthly_income=2_000, income_type="pension")
        self.expense(screen, 1_500, "rent")

        self.assert_eligible(self.calculate(screen), 25 * 12)

    def test_same_household_at_59_fails_the_gross_test(self):
        screen = self.single(age=59, monthly_income=2_000, income_type="pension")
        self.expense(screen, 1_500, "rent")

        self.assert_ineligible(self.calculate(screen))

    def test_gross_test_is_skipped_for_each_disability_flag(self):
        for flag in ("disabled", "visually_impaired", "long_term_disability"):
            with self.subTest(flag):
                screen = self.single(monthly_income=2_000, income_type="pension", **{flag: True})
                self.expense(screen, 1_500, "rent")

                self.assertTrue(self.calculate(screen).eligible)

    def test_gross_test_is_skipped_for_a_member_reporting_ssdi(self):
        screen = self.single(age=40)
        self.add_income(self.head_of(screen), 2_000, "sSDisability")
        self.expense(screen, 1_500, "rent")

        self.assertTrue(self.calculate(screen).eligible)

    def test_another_member_being_elderly_is_enough(self):
        screen = self.household(
            ("headOfHousehold", 40, {"monthly_income": 2_000, "income_type": "pension"}),
            ("parent", 70),
        )
        self.expense(screen, 1_500, "rent")

        self.assertTrue(self.calculate(screen).eligible)


class TestResourceLimit(MfbSnapTestCase):
    def test_resources_at_3000_pass(self):
        self.assert_eligible(self.calculate(self.single(assets=3_000)), 306 * 12)

    def test_resources_over_3000_fail(self):
        self.assert_ineligible(self.calculate(self.single(assets=3_001)))

    def test_resources_at_4750_pass_with_an_elderly_member(self):
        self.assertTrue(self.calculate(self.single(age=60, assets=4_750)).eligible)

    def test_resources_over_4750_fail_with_an_elderly_member(self):
        self.assert_ineligible(self.calculate(self.single(age=60, assets=4_751)))

    def test_resources_at_4750_pass_with_a_disabled_member(self):
        self.assertTrue(self.calculate(self.single(assets=4_750, disabled=True)).eligible)

    def test_resources_over_3000_fail_without_an_elderly_or_disabled_member(self):
        self.assert_ineligible(self.calculate(self.single(age=59, assets=4_750)))


class TestCategoricalEligibility(MfbSnapTestCase):
    def test_cash_assistance_income_passes_without_the_income_tests(self):
        # 3,600 gross is over the limit and net is over 1,330 too; only the receipt lets it through.
        screen = self.single(monthly_income=3_000)
        self.add_income(self.head_of(screen), 600, "cashAssistance")

        self.assert_eligible(self.calculate(screen), 25 * 12)

    def test_ssi_income_passes_without_the_income_tests(self):
        screen = self.single(monthly_income=3_000, income_type="sSI")

        self.assert_eligible(self.calculate(screen), 25 * 12)

    def test_tanf_tile_passes_without_the_income_tests(self):
        screen = self.single(monthly_income=4_000)

        with patch.object(Screen, "has_base_benefit", lambda _screen, base: reports_tanf_tile(base)):
            self.assert_eligible(self.calculate(screen), 25 * 12)

    def test_same_household_without_receipt_fails(self):
        screen = self.single(monthly_income=4_000)

        self.assert_ineligible(self.calculate(screen))

    def test_a_non_tanf_benefit_tile_is_not_receipt(self):
        screen = self.single(monthly_income=4_000)

        with patch.object(Screen, "has_base_benefit", lambda _screen, base: base == "wic"):
            self.assert_ineligible(self.calculate(screen))

    def test_household_of_three_with_a_positive_allotment_passes(self):
        # Cash assistance adds 100 unearned: net = 3,100 - 600 - 217 = 2,283; 30% rounds up to 685;
        # 808 - 685 = 123. Gross 3,100 is over the 2,960 limit, so only the categorical route lets it through.
        screen = self.household(
            ("headOfHousehold", 30, {"monthly_income": 3_000}),
            ("child", 5),
            ("child", 3),
        )
        self.add_income(self.head_of(screen), 100, "cashAssistance")

        self.assert_eligible(self.calculate(screen), (808 - 685) * 12)

    def test_household_of_three_with_a_zero_allotment_does_not_pass(self):
        # Net 4,000 - 800 - 217 = 2,983; 30% rounds up to 895, over the 808 maximum.
        screen = self.household(
            ("headOfHousehold", 30, {"monthly_income": 4_000}),
            ("child", 5),
            ("child", 3),
        )
        self.add_income(self.head_of(screen), 100, "cashAssistance")

        self.assert_ineligible(self.calculate(screen))

    def test_household_of_two_passes_whatever_the_allotment(self):
        screen = self.household(
            ("headOfHousehold", 30, {"monthly_income": 4_000}),
            ("child", 5),
        )
        self.add_income(self.head_of(screen), 100, "cashAssistance")

        self.assert_eligible(self.calculate(screen), 25 * 12)

    def test_a_state_can_add_a_route(self):
        screen = self.single(monthly_income=4_000)
        self.add_income(self.head_of(screen), 100, "generalAssistance")

        self.assert_ineligible(self.calculate(screen))

        original = self.calculator_class
        self.calculator_class = StandInSnapWithExtraRoute
        try:
            self.assertTrue(self.calculate(screen).eligible)
        finally:
            self.calculator_class = original


class TestStudentRule(MfbSnapTestCase):
    """A full-time student with no exception is left out of the household entirely."""

    FULL_TIME = {"student": True, "student_full_time": True}

    def student_household(self, student_age: int = 22, **student_kwargs):
        """A head with 1,000 a month and a full-time student, listed as a sibling."""
        screen = self.household(
            ("headOfHousehold", 40, {"monthly_income": 1_000}),
            ("sisterOrBrother", student_age, {**self.FULL_TIME, "monthly_income": 5_000, **student_kwargs}),
        )

        return screen, self.calculator(screen)

    def test_student_is_left_out_of_size_and_income(self):
        screen, calculator = self.student_household()

        self.assertEqual(len(calculator.ineligible_students), 1)
        self.assertEqual(calculator.household_size, 1)
        self.assertEqual(calculator.countable_income, 1_000)

    def test_rest_of_the_household_still_receives_as_a_household_of_one(self):
        screen, _ = self.student_household()

        self.assert_eligible(self.calculate(screen), 131 * 12)

    def test_student_is_left_out_on_the_categorical_route_too(self):
        # Three listed, one student: a household of two, so the allotment check does not apply.
        screen = self.household(
            ("headOfHousehold", 40, {"monthly_income": 4_000}),
            ("child", 5),
            ("sisterOrBrother", 22, self.FULL_TIME),
        )
        # SSI, not cash assistance: reported cash assistance would itself excuse the student.
        self.add_income(self.head_of(screen), 100, "sSI")

        self.assertEqual(self.calculator(screen).household_size, 2)
        self.assert_eligible(self.calculate(screen), 25 * 12)

    def test_household_of_only_ineligible_students_is_ineligible(self):
        screen = self.household(("headOfHousehold", 22, self.FULL_TIME))

        self.assertEqual(self.calculator(screen).household_size, 0)
        self.assert_ineligible(self.calculate(screen))

    def test_student_not_full_time_is_counted(self):
        for full_time in (False, None):
            with self.subTest(student_full_time=full_time):
                _, calculator = self.student_household(student_full_time=full_time)

                self.assertEqual(calculator.ineligible_students, [])

    def test_non_student_is_counted(self):
        _, calculator = self.student_household(student=False)

        self.assertEqual(calculator.ineligible_students, [])

    def test_student_under_18_or_50_and_over_is_excused(self):
        for age, left_out in ((17, False), (18, True), (49, True), (50, False)):
            with self.subTest(age=age):
                _, calculator = self.student_household(student_age=age)

                self.assertEqual(bool(calculator.ineligible_students), left_out)

    def test_each_exception_keeps_the_student_in(self):
        exceptions = {
            "disabled": {"disabled": True},
            "visually impaired": {"visually_impaired": True},
            "long-term disability": {"long_term_disability": True},
            "works 20 hours": {"student_works_20_plus_hrs": True},
            "work study": {"student_has_work_study": True},
            "job training": {"student_job_training_program": True},
        }
        for name, kwargs in exceptions.items():
            with self.subTest(name):
                _, calculator = self.student_household(**kwargs)

                self.assertEqual(calculator.ineligible_students, [])

    def test_tanf_receipt_keeps_the_student_in(self):
        _, calculator = self.student_household()
        self.assertEqual(len(calculator.ineligible_students), 1)

        with patch.object(Screen, "has_base_benefit", lambda _screen, base: reports_tanf_tile(base)):
            self.assertEqual(calculator.is_ineligible_student(calculator.members[1]), False)

    def test_cash_assistance_income_keeps_the_student_in(self):
        screen, _ = self.student_household()
        self.add_income(self.head_of(screen), 50, "cashAssistance")

        self.assertEqual(self.calculator(screen).ineligible_students, [])

    def test_head_with_a_child_under_6_is_excused(self):
        screen = self.household(
            ("headOfHousehold", 30, self.FULL_TIME),
            ("child", 5),
        )

        self.assertEqual(self.calculator(screen).ineligible_students, [])

    def test_spouse_with_a_child_under_6_is_excused(self):
        screen = self.household(
            ("headOfHousehold", 30),
            ("spouse", 30, self.FULL_TIME),
            ("child", 5),
        )

        self.assertEqual(self.calculator(screen).ineligible_students, [])

    def test_domestic_partner_with_a_child_under_6_is_excused(self):
        screen = self.household(
            ("headOfHousehold", 30),
            ("domesticPartner", 30, self.FULL_TIME),
            ("child", 5),
        )

        self.assertEqual(self.calculator(screen).ineligible_students, [])

    def test_single_head_with_a_child_under_12_is_excused(self):
        screen = self.household(
            ("headOfHousehold", 30, self.FULL_TIME),
            ("child", 11),
        )

        self.assertEqual(self.calculator(screen).ineligible_students, [])

    def test_head_with_a_partner_and_a_child_6_to_11_is_left_out(self):
        screen = self.household(
            ("headOfHousehold", 30, self.FULL_TIME),
            ("spouse", 30),
            ("child", 8),
        )

        self.assertEqual(len(self.calculator(screen).ineligible_students), 1)

    def test_single_head_with_a_child_12_or_older_is_left_out(self):
        screen = self.household(
            ("headOfHousehold", 30, self.FULL_TIME),
            ("child", 12),
        )

        self.assertEqual(len(self.calculator(screen).ineligible_students), 1)

    def test_a_student_who_is_not_a_head_spouse_or_partner_gets_no_parent_exception(self):
        screen = self.household(
            ("headOfHousehold", 40),
            ("sisterOrBrother", 22, self.FULL_TIME),
            ("child", 3),
        )

        self.assertEqual(len(self.calculator(screen).ineligible_students), 1)

    def test_student_with_unknown_age_gets_no_age_exception(self):
        screen = self.household(
            ("headOfHousehold", 40),
            ("sisterOrBrother", 22, self.FULL_TIME),
        )
        sibling = screen.household_members.get(relationship="sisterOrBrother")
        self.set_age(sibling, None)

        self.assertEqual(len(self.calculator(screen).ineligible_students), 1)


class TestValueAndDependencies(MfbSnapTestCase):
    def test_value_is_annual(self):
        self.assertEqual(self.calculate(self.single()).value, 306 * 12)

    def test_value_for_a_large_household_uses_the_extended_maximum_allotment(self):
        screen = self.make_screen(household_size=10)
        for _ in range(10):
            self.add_member(screen, "child", 5)

        self.assertEqual(self.calculator(screen).allotment(), 1841 + 225 * 2)

    def test_allotment_rounds_thirty_percent_of_net_income_up(self):
        # Net 583.0 * 0.3 = 174.9 -> 175, not 174.
        self.assertEqual(self.calculator(self.single(monthly_income=1_000)).allotment(), 306 - 175)

    def test_calculator_declares_every_field_it_reads(self):
        for field in (
            "household_size",
            "household_assets",
            "age",
            "relationship",
            "student",
            "disabled",
            "income_amount",
            "expense_amount",
        ):
            with self.subTest(field):
                self.assertIn(field, MfbSnap.dependencies)

    def test_a_missing_declared_field_drops_the_program(self):
        screen = self.single()

        self.assertFalse(self.make_calculator(screen, missing=("age",)).can_calc())
        self.assertFalse(self.make_calculator(screen, missing=("expense_amount",)).can_calc())

    def test_undeclared_fields_do_not_drop_the_program(self):
        screen = self.single()

        self.assertTrue(self.make_calculator(screen, missing=("pregnant",)).can_calc())
