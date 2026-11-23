"""Federal Pell Grant scenarios, one per spec section 8, plus the formula helpers.

Poverty lines are the 2026 48-state guidelines, the program's year. Each scenario's household
is built from the spec's steps: members with their relationship to the head, age, wages and
flags, and the household's assets.

Section 4's `citizenship` has no test here: it is enforced by the program record's
`legal_status_required`, which the calculator never reads.
"""

from datetime import date
from decimal import Decimal

from programs.framework.base import Eligibility
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.pell_grant.calculator import (
    IPA_FAMILY_A2,
    IPA_MARRIED_C2,
    IPA_SINGLE_PARENT_C3,
    MAX_PELL,
    MIN_PELL,
    PellGrant,
    allowance,
    contribution_from_aai,
    payroll_allowance,
    round_to_5,
    whole,
)
from screener.models import HouseholdMember, Screen

STUDENT = {"student": True}


class PellGrantTestCase(CustomCalculatorTestCase):
    calculator_class = PellGrant
    white_label_code = "federal"
    state_code = ""
    fpl_year = "2026"
    stores_age = False
    # Ages are stated as of the 2026-27 award year; the age-24 test reads December 31, 2026.
    reference_date = date(2026, 9, 1)

    def household(self, *members: tuple, assets: int = 0) -> Screen:
        """A household of `(relationship, age, wages, flags)` members.

        `flags` may carry member fields (`student`, `was_in_foster_care`) and `income`, a dict of
        further yearly income streams by type.
        """
        screen = self.make_screen(household_size=len(members), household_assets=assets)
        for relationship, age, wages, *rest in members:
            flags = dict(rest[0]) if rest else {}
            income = flags.pop("income", {})
            member = self.add_member(screen, relationship, age=age, yearly_income=wages, **flags)
            for income_type, amount in income.items():
                self.add_income(member, amount, income_type=income_type, frequency="yearly")

        return screen

    def member(self, screen: Screen, index: int) -> HouseholdMember:
        return screen.household_members.order_by("id")[index]

    def assert_award(self, e: Eligibility, value: int) -> None:
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assert_ineligible(self, e: Eligibility) -> None:
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestRegistration(PellGrantTestCase):
    def test_program_code_is_the_prefixed_federal_name(self):
        self.assertEqual(PellGrant.program_code, "federal_pell_grant")

    def test_award_bounds(self):
        self.assertEqual((MAX_PELL, MIN_PELL), (7_395, 740))

    def test_household_assets_is_not_a_dependency(self):
        """A blank asset answer counts as $0 rather than dropping the program."""
        self.assertNotIn("household_assets", PellGrant.dependencies)

    def test_a_missing_student_answer_drops_the_program(self):
        screen = self.household(("headOfHousehold", 30, 20_000, STUDENT))

        self.assertFalse(self.make_calculator(screen, missing=("student",)).can_calc())


class TestScenarios(PellGrantTestCase):
    def test_scenario_1_independent_student_under_the_maximum_line(self):
        screen = self.household(("headOfHousehold", 30, 20_000, STUDENT))

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_2_not_a_student(self):
        screen = self.household(("headOfHousehold", 30, 20_000))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_3_exactly_at_175_percent(self):
        screen = self.household(("headOfHousehold", 30, 27_930, STUDENT))

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_4_single_parent_at_225_percent(self):
        screen = self.household(
            ("headOfHousehold", 28, 48_690, STUDENT),
            ("child", 4, 0),
            assets=220_000,
        )

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_5_dependent_student_parents_at_175_percent_for_four(self):
        screen = self.household(
            ("headOfHousehold", 45, 30_000),
            ("spouse", 44, 27_750),
            ("child", 19, 0, STUDENT),
            ("child", 15, 0),
        )

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_6_dependent_student_parents_far_above_every_line(self):
        screen = self.household(
            ("headOfHousehold", 50, 120_000),
            ("spouse", 49, 80_000),
            ("child", 19, 0, STUDENT),
            ("child", 15, 0),
        )
        calculator = self.make_calculator(screen)
        student = self.member(screen, 2)

        self.assertEqual(calculator.student_aid_index(student, calculator.family(student)), 54_602)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_7_independent_at_25_with_a_high_earning_parent(self):
        screen = self.household(
            ("headOfHousehold", 25, 27_900, STUDENT),
            ("parent", 52, 150_000),
        )

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_8_independent_student_on_the_sai_path(self):
        screen = self.household(("headOfHousehold", 30, 32_000, STUDENT))

        self.assert_award(self.calculate(screen), 1_775)

    def test_scenario_9_exactly_at_the_minimum_award_line(self):
        screen = self.household(("headOfHousehold", 30, 43_890, STUDENT))

        self.assert_award(self.calculate(screen), 740)

    def test_scenario_10_one_dollar_over_the_minimum_award_line(self):
        screen = self.household(("headOfHousehold", 30, 43_891, STUDENT))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_11_savings_put_the_sai_at_the_cutoff(self):
        screen = self.household(("headOfHousehold", 30, 40_000, STUDENT), assets=27_375)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_12_five_dollars_less_in_savings(self):
        screen = self.household(("headOfHousehold", 30, 40_000, STUDENT), assets=27_370)

        self.assert_award(self.calculate(screen), 740)

    def test_scenario_13_low_income_student_with_savings_gets_the_maximum(self):
        screen = self.household(("headOfHousehold", 30, 20_000, STUDENT), assets=73_550)

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_14_dependent_head_with_a_single_parent(self):
        screen = self.household(
            ("headOfHousehold", 19, 0, STUDENT),
            ("parent", 48, 48_690),
        )

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_15_dependent_head_with_a_high_earning_parent(self):
        screen = self.household(
            ("headOfHousehold", 19, 0, STUDENT),
            ("parent", 48, 150_000),
        )
        calculator = self.make_calculator(screen)
        student = self.member(screen, 0)

        self.assertEqual(calculator.student_aid_index(student, calculator.family(student)), 40_274)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_16_dependent_student_with_no_parent(self):
        screen = self.household(
            ("headOfHousehold", 20, 0, STUDENT),
            ("roommate", 21, 30_000),
        )

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_17_only_a_stepparent_at_home(self):
        screen = self.household(
            ("headOfHousehold", 19, 0, STUDENT),
            ("stepParent", 45, 30_000),
        )

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_18_married_independent_student(self):
        screen = self.household(
            ("headOfHousehold", 22, 45_000, STUDENT),
            ("spouse", 23, 0),
        )

        self.assert_award(self.calculate(screen), 3_790)

    def test_scenario_19_former_foster_youth_with_a_high_earning_parent(self):
        screen = self.household(
            ("headOfHousehold", 20, 25_000, {**STUDENT, "was_in_foster_care": True}),
            ("parent", 50, 150_000),
        )

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_20_student_aged_22_living_with_a_parent(self):
        screen = self.household(
            ("headOfHousehold", 22, 20_000, STUDENT),
            ("parent", 52, 150_000),
        )
        calculator = self.make_calculator(screen)
        student = self.member(screen, 0)

        self.assertEqual(calculator.student_aid_index(student, calculator.family(student)), 43_624)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_21_one_dollar_over_the_maximum_line(self):
        screen = self.household(("headOfHousehold", 30, 27_931, STUDENT))

        self.assert_award(self.calculate(screen), 3_655)

    def test_scenario_22_no_income_and_savings(self):
        screen = self.household(("headOfHousehold", 30, 0, STUDENT), assets=50_000)

        self.assert_award(self.calculate(screen), 6_550)

    def test_scenario_23_sai_award_under_the_minimum(self):
        screen = self.household(("headOfHousehold", 30, 35_000, STUDENT))

        self.assert_award(self.calculate(screen), 740)

    def test_scenario_24_two_students_in_one_household(self):
        screen = self.household(
            ("headOfHousehold", 45, 30_000),
            ("spouse", 44, 27_750),
            ("child", 19, 0, STUDENT),
            ("child", 15, 0),
            ("child", 25, 32_000, STUDENT),
        )
        calculator = self.make_calculator(screen)

        self.assertEqual(calculator.award(self.member(screen, 2)), 7_395)
        self.assertEqual(calculator.award(self.member(screen, 4)), 1_775)
        self.assert_award(self.calculate(screen), 9_170)

    def test_scenario_25_dependent_student_reduced_award(self):
        screen = self.household(
            ("headOfHousehold", 45, 55_000),
            ("spouse", 44, 0),
            ("child", 19, 0, STUDENT),
        )

        self.assert_award(self.calculate(screen), 5_315)

    def test_scenario_26_single_parent_student_reduced_award(self):
        screen = self.household(
            ("headOfHousehold", 30, 75_000, STUDENT),
            ("child", 5, 0),
        )

        self.assert_award(self.calculate(screen), 5_345)

    def test_scenario_27_single_parent_exactly_at_325_percent(self):
        screen = self.household(
            ("headOfHousehold", 48, 70_330),
            ("child", 19, 0, STUDENT),
        )

        self.assert_award(self.calculate(screen), 740)

    def test_scenario_28_two_parents_exactly_at_275_percent(self):
        screen = self.household(
            ("headOfHousehold", 45, 75_130),
            ("spouse", 44, 0),
            ("child", 19, 0, STUDENT),
            assets=8_000,
        )

        self.assert_award(self.calculate(screen), 740)

    def test_scenario_29_single_parent_student_exactly_at_400_percent(self):
        screen = self.household(
            ("headOfHousehold", 30, 86_560, STUDENT),
            ("child", 5, 0),
            assets=130_000,
        )

        self.assert_award(self.calculate(screen), 740)

    def test_scenario_30_married_student_with_a_child_exactly_at_350_percent(self):
        screen = self.household(
            ("headOfHousehold", 30, 95_620, STUDENT),
            ("spouse", 30, 0),
            ("child", 5, 0),
            assets=50_000,
        )

        self.assert_award(self.calculate(screen), 740)

    def test_scenario_31_ssi_is_left_out_of_income(self):
        screen = self.household(("headOfHousehold", 30, 20_000, {**STUDENT, "income": {"sSI": 10_000}}))

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_32_one_dollar_over_the_single_parent_maximum_line(self):
        screen = self.household(
            ("headOfHousehold", 19, 0, STUDENT),
            ("parent", 48, 48_691),
        )

        self.assert_award(self.calculate(screen), 5_025)

    def test_scenario_33_single_parent_one_dollar_over_325_percent(self):
        screen = self.household(
            ("headOfHousehold", 48, 70_331),
            ("child", 19, 0, STUDENT),
        )

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_34_two_parents_one_dollar_over_275_percent(self):
        screen = self.household(
            ("headOfHousehold", 45, 75_131),
            ("spouse", 44, 0),
            ("child", 19, 0, STUDENT),
            assets=8_000,
        )

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_35_single_parent_student_one_dollar_over_400_percent(self):
        screen = self.household(
            ("headOfHousehold", 30, 86_561, STUDENT),
            ("child", 5, 0),
            assets=130_000,
        )

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_36_married_student_with_a_child_one_dollar_over_350_percent(self):
        screen = self.household(
            ("headOfHousehold", 30, 95_621, STUDENT),
            ("spouse", 30, 0),
            ("child", 5, 0),
            assets=50_000,
        )

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_37_a_child_makes_a_20_year_old_independent(self):
        screen = self.household(
            ("headOfHousehold", 20, 20_000, STUDENT),
            ("child", 2, 0),
            ("parent", 50, 150_000),
        )

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_38_child_support_counts_with_assets(self):
        screen = self.household(
            ("headOfHousehold", 30, 75_000, {**STUDENT, "income": {"childSupport": 12_000}}),
            ("child", 5, 0),
        )

        self.assert_award(self.calculate(screen), 5_160)

    def test_scenario_39_domestic_partner_reads_as_married(self):
        screen = self.household(
            ("headOfHousehold", 22, 30_000, STUDENT),
            ("domesticPartner", 23, 15_000),
            ("parent", 50, 150_000),
        )

        self.assert_award(self.calculate(screen), 3_790)

    def test_scenario_40_student_married_to_the_head(self):
        screen = self.household(
            ("headOfHousehold", 30, 30_000),
            ("spouse", 22, 15_000, STUDENT),
        )

        self.assert_award(self.calculate(screen), 3_790)

    def test_scenario_41_parent_and_stepparent_at_home(self):
        screen = self.household(
            ("headOfHousehold", 20, 0, STUDENT),
            ("parent", 47, 30_000),
            ("stepParent", 48, 25_000),
        )

        self.assert_award(self.calculate(screen), 5_315)

    def test_scenario_42_sai_exactly_6655(self):
        screen = self.household(
            ("headOfHousehold", 30, 94_000, STUDENT),
            ("child", 5, 0),
            assets=30_125,
        )
        calculator = self.make_calculator(screen)
        student = self.member(screen, 0)

        self.assertEqual(calculator.student_aid_index(student, calculator.family(student)), 6_655)
        self.assert_award(self.calculate(screen), 740)

    def test_scenario_43_sai_6656(self):
        screen = self.household(
            ("headOfHousehold", 30, 94_000, STUDENT),
            ("child", 5, 0),
            assets=30_165,
        )
        calculator = self.make_calculator(screen)
        student = self.member(screen, 0)

        self.assertEqual(calculator.student_aid_index(student, calculator.family(student)), 6_656)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_44_parents_one_dollar_over_175_percent_for_four(self):
        screen = self.household(
            ("headOfHousehold", 45, 30_001),
            ("spouse", 44, 27_750),
            ("child", 19, 0, STUDENT),
            ("child", 15, 0),
        )

        self.assert_award(self.calculate(screen), 6_635)

    def test_scenario_45_parent_with_a_domestic_partner(self):
        screen = self.household(
            ("headOfHousehold", 45, 50_000),
            ("domesticPartner", 46, 40_000),
            ("child", 19, 0, STUDENT),
        )

        self.assert_award(self.calculate(screen), 7_395)

    def test_scenario_46_grandchild_student_has_no_parent_identified(self):
        screen = self.household(
            ("headOfHousehold", 66, 25_000),
            ("child", 42, 20_000),
            ("grandChild", 19, 0, STUDENT),
        )

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_47_spouse_entered_as_an_in_law(self):
        screen = self.household(
            ("headOfHousehold", 50, 150_000),
            ("child", 22, 15_000, STUDENT),
            ("relatedOther", 23, 20_000),
        )
        calculator = self.make_calculator(screen)
        student = self.member(screen, 1)

        self.assertEqual(calculator.student_aid_index(student, calculator.family(student)), 37_960)
        self.assert_ineligible(self.calculate(screen))

    def test_scenario_48_veterans_benefits_are_left_out_of_income(self):
        screen = self.household(("headOfHousehold", 30, 20_000, {**STUDENT, "income": {"veteran": 15_000}}))

        self.assert_award(self.calculate(screen), 7_395)


class TestEdges(PellGrantTestCase):
    def test_age_24_by_the_end_of_the_award_year_is_independent(self):
        """Born in December 2002: 23 on the screening date, 24 by December 31, 2026."""
        screen = self.make_screen(household_size=2)
        self.add_member(
            screen, "headOfHousehold", age=None, birth_year_month=date(2002, 12, 1), yearly_income=20_000, student=True
        )
        self.add_member(screen, "parent", age=52, yearly_income=150_000)

        self.assert_award(self.calculate(screen), 7_395)

    def test_age_23_at_the_end_of_the_award_year_is_dependent(self):
        screen = self.make_screen(household_size=2)
        self.add_member(
            screen, "headOfHousehold", age=None, birth_year_month=date(2003, 1, 1), yearly_income=20_000, student=True
        )
        self.add_member(screen, "parent", age=52, yearly_income=150_000)

        self.assert_ineligible(self.calculate(screen))

    def test_blank_household_assets_count_as_zero(self):
        screen = self.household(("headOfHousehold", 30, 32_000, STUDENT))
        screen.household_assets = None
        screen.save()

        self.assert_award(self.calculate(screen), 1_775)

    def test_a_student_not_answered_is_not_a_student(self):
        screen = self.household(("headOfHousehold", 30, 20_000, {"student": None}))

        self.assert_ineligible(self.calculate(screen))

    def test_a_non_student_in_the_household_is_not_paid(self):
        screen = self.household(
            ("headOfHousehold", 30, 20_000, STUDENT),
            ("spouse", 30, 0),
        )
        calculator = self.make_calculator(screen)
        e = calculator.calc()

        self.assertEqual([m.value for m in e.eligible_members if m.eligible], [7_395])


class TestHelpers(PellGrantTestCase):
    needs_program_row = False

    def test_whole_rounds_half_away_from_zero(self):
        self.assertEqual(whole(Decimal("10.5")), 11)
        self.assertEqual(whole(Decimal("-11.5")), -12)
        self.assertEqual(whole(Decimal("-11.449")), -11)
        self.assertEqual(whole(Decimal("10.4995")), 11)  # 10.500 at three decimals

    def test_round_to_5(self):
        self.assertEqual([round_to_5(n) for n in (1_772, 1_773, 1_774, 1_775)], [1_770, 1_775, 1_775, 1_775])

    def test_payroll_allowance(self):
        self.assertEqual(payroll_allowance(Decimal(32_000), joint=False), 464 + 1_984)
        # Over the single OASDI base and the single Medicare threshold.
        self.assertEqual(payroll_allowance(Decimal(210_000), joint=False), 2_900 + 235 + 10_453)
        # The joint base and threshold reach further.
        self.assertEqual(payroll_allowance(Decimal(210_000), joint=True), 3_045 + 13_020)
        self.assertEqual(payroll_allowance(Decimal(-5_000), joint=False), 0)

    def test_contribution_from_aai_brackets(self):
        self.assertEqual(contribution_from_aai(-8_501), -1_870)
        self.assertEqual(contribution_from_aai(-8_500), -1_870)
        self.assertEqual(contribution_from_aai(9_462), 2_082)
        self.assertEqual(contribution_from_aai(21_800), 4_796)
        self.assertEqual(contribution_from_aai(21_801), 4_796)
        self.assertEqual(contribution_from_aai(27_301), 6_171)
        self.assertEqual(contribution_from_aai(32_801), 7_766)
        self.assertEqual(contribution_from_aai(38_401), 9_670)
        self.assertEqual(contribution_from_aai(43_901), 11_870)
        self.assertEqual(contribution_from_aai(134_820), 54_602)

    def test_allowance_tables_extend_past_their_last_row(self):
        self.assertEqual(allowance(IPA_FAMILY_A2, 4), 44_880)
        self.assertEqual(allowance(IPA_FAMILY_A2, 8), 61_930 + 2 * 6_990)
        self.assertEqual(allowance(IPA_MARRIED_C2, 7), 98_370 + 11_110)
        self.assertEqual(allowance(IPA_SINGLE_PARENT_C3, 2), 54_950)

    def test_allowance_tables_floor_at_their_first_row(self):
        self.assertEqual(allowance(IPA_FAMILY_A2, 1), 29_190)
        self.assertEqual(allowance(IPA_MARRIED_C2, 2), 57_730)
