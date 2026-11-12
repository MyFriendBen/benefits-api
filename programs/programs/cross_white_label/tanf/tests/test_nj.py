"""
NJ TANF, Work First New Jersey (``NjTanf``): NJ's values, the proxy assistance unit, and one test per
Test Scenario in the NJ spec (``programs/cross_white_label/tanf/nj/tanf_nj_spec.md`` in program-ops).

The spec states monthly values, some in cents ($139.50). The API reports whole annual dollars, so
each test asserts the monthly figure times 12, rounded half-up.

Every scenario sits in ZIP 08608, Mercer County, which no rule reads.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Union

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.tanf.mfb_base import MfbTanf
from programs.programs.cross_white_label.tanf.nj import NjTanf
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import HouseholdMember, Screen

Income = dict[str, Union[int, str]]


def annual(monthly: Union[int, str]) -> int:
    return int((Decimal(str(monthly)) * 12).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class NjTanfTestCase(CustomCalculatorTestCase):
    calculator_class = NjTanf
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "08608"
    default_county = "Mercer County"
    needs_program_row = False
    stores_age = False

    def household(self, *members: tuple, assets: int = 0, child_support_paid: int = 0) -> Screen:
        """
        A screen from (relationship, age) or (relationship, age, {income type: monthly amount})
        tuples, the head first.
        """
        screen = self.make_screen(household_size=len(members), household_assets=assets)
        for spec in members:
            relationship, age = spec[0], spec[1]
            incomes = spec[2] if len(spec) > 2 else {}
            member = self.add_member(screen, relationship, age)
            for income_type, amount in incomes.items():
                self.add_income(member, amount, income_type)

        if child_support_paid:
            self.add_expense(screen.get_head(), child_support_paid, "childSupport")

        return screen

    def assert_eligible(self, eligibility: Eligibility, monthly: Union[int, str]) -> None:
        self.assertTrue(eligibility.eligible, eligibility.fail_messages)
        self.assertEqual(eligibility.value, annual(monthly))

    def assert_ineligible(self, eligibility: Eligibility) -> None:
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def unit_size(self, screen: Screen) -> int:
        return self.make_calculator(screen).assistance_unit().size


HEAD = "headOfHousehold"


def head(age: int = 30, incomes: Optional[Income] = None) -> tuple:
    return (HEAD, age, incomes or {})


class TestNjValues(NjTanfTestCase):
    def test_extends_the_base(self):
        self.assertTrue(issubclass(NjTanf, MfbTanf))

    def test_program_code(self):
        self.assertEqual(NjTanf.program_code, "nj_tanf")

    def test_constants(self):
        self.assertFalse(NjTanf.serves_pregnant_individual)
        self.assertEqual(NjTanf.resource_limit, 2_000)
        self.assertEqual(NjTanf.earned_income_disregard, Decimal("0.50"))
        self.assertEqual(NjTanf.one_child_pass_through, 100)
        self.assertEqual(NjTanf.two_child_pass_through, 200)

    def test_schedules(self):
        self.assertEqual(NjTanf.schedule_i, {1: 321, 2: 638, 3: 839, 4: 966, 5: 1_092, 6: 1_221, 7: 1_341, 8: 1_442})
        self.assertEqual(NjTanf.schedule_ii, {1: 214, 2: 425, 3: 559, 4: 644, 5: 728, 6: 814, 7: 894, 8: 961})

    def test_additional_person_beyond_the_tables(self):
        # The screener stops at 8, so no scenario reaches these.
        self.assertEqual(NjTanf._by_size(NjTanf.schedule_i, NjTanf.schedule_i_additional_person, 10), 1_640)
        self.assertEqual(NjTanf._by_size(NjTanf.schedule_ii, NjTanf.schedule_ii_additional_person, 10), 1_093)

    def test_dependencies(self):
        self.assertEqual(
            set(NjTanf.dependencies),
            {
                "age",
                "relationship",
                "household_assets",
                "income_type",
                "income_amount",
                "income_frequency",
                "expense_type",
                "expense_amount",
                "expense_frequency",
            },
        )

    def test_missing_expense_answers_skip_the_program(self):
        calculator = self.make_calculator(self.household(head(), ("child", 5)), missing=("expense_amount",))

        self.assertFalse(calculator.can_calc())


class TestAssistanceUnit(NjTanfTestCase):
    """The proxy unit's composition, beyond what the scenarios pin."""

    def test_every_provisional_relative_counts_through_18(self):
        for relationship in (
            "stepChild",
            "grandChild",
            "fosterChild",
            "sisterOrBrother",
            "stepSisterOrBrother",
            "relatedOther",
        ):
            with self.subTest(relationship=relationship):
                self.assertEqual(self.unit_size(self.household(head(), ("child", 5), (relationship, 18))), 3)
                self.assertEqual(self.unit_size(self.household(head(), ("child", 5), (relationship, 19))), 2)

    def test_excluded_relationships(self):
        for relationship in (
            "parent",
            "grandParent",
            "stepParent",
            "fosterParent",
            "boyfriendOrGirlfriend",
            "domesticPartner",
            "roommate",
        ):
            with self.subTest(relationship=relationship):
                self.assertEqual(self.unit_size(self.household(head(), ("child", 5), (relationship, 10))), 2)

    def test_a_spouse_is_in_the_unit(self):
        self.assertEqual(self.unit_size(self.household(head(), ("spouse", 30), ("child", 5))), 3)

    def test_child_only_case_leaves_out_the_spouse_and_their_income(self):
        screen = self.household(head(60), ("spouse", 62, {"wages": 3_000}), ("grandChild", 8))

        self.assertEqual(self.unit_size(screen), 1)
        self.assert_eligible(self.calculate(screen), 214)

    def test_an_adult_child_keeps_the_head_in_the_unit(self):
        # Scenario 43's shape: a `child` of any age means the head is a parent, not a caretaker.
        self.assertEqual(self.unit_size(self.household(head(50), ("child", 25), ("grandChild", 1))), 2)

    def test_an_ssi_child_qualifies_a_non_ssi_spouse_when_the_head_receives_ssi(self):
        screen = self.household(head(40, {"sSI": 994}), ("spouse", 40), ("child", 10, {"sSI": 994}))

        self.assert_eligible(self.calculate(screen), 214)

    def test_an_ssi_child_does_not_qualify_ssi_parents(self):
        screen = self.household(head(40, {"sSI": 994}), ("spouse", 40, {"sSI": 994}), ("child", 10, {"sSI": 994}))

        self.assert_ineligible(self.calculate(screen))

    def test_an_ssi_grandchild_does_not_qualify_the_caretaker(self):
        self.assert_ineligible(self.calculate(self.household(head(60), ("grandChild", 8, {"sSI": 994}))))

    def test_an_ssi_head_with_a_spouse_in_the_unit_has_income_counted(self):
        # The SSI head is the spouse of a unit member (3.12(a)): wages gross, unemployment in full.
        screen = self.household(head(40, {"sSI": 994, "wages": 100, "unemployment": 50}), ("spouse", 40), ("child", 5))

        self.assertEqual(self.unit_size(screen), 2)
        self.assert_eligible(self.calculate(screen), 425 - 150)

    def test_an_ssi_spouses_child_support_is_not_counted(self):
        screen = self.household(head(32), ("spouse", 33, {"sSI": 994, "childSupport": 300}), ("child", 5))

        self.assert_eligible(self.calculate(screen), 425)

    def test_an_ssi_head_parents_child_support_counts_for_the_child(self):
        screen = self.household(head(35, {"sSI": 994, "childSupport": 300}), ("child", 9))

        self.assert_eligible(self.calculate(screen), 214 - 200)

    def test_child_support_paid_is_read_from_any_member(self):
        screen = self.household(head(30, {"unemployment": 700}), ("child", 6))
        self.add_expense(screen.household_members.get(relationship="child"), 300, "childSupport")

        self.assert_eligible(self.calculate(screen), 25)

    def test_other_expenses_are_not_child_support_paid(self):
        screen = self.household(head(30, {"unemployment": 400}), ("child", 6))
        self.add_expense(screen.get_head(), 300, "rent")

        self.assert_eligible(self.calculate(screen), 25)


class TestIncomeCounting(NjTanfTestCase):
    def test_weekly_wages_are_converted_to_monthly(self):
        screen = self.household(head(), ("child", 6))
        self.add_income(screen.get_head(), 100, "wages", "weekly")

        # $435 a month; Schedule II counts half.
        self.assert_eligible(self.calculate(screen), "207.50")

    def test_other_unearned_income_counts_in_full(self):
        for income_type in ("sSDisability", "sSRetirement", "pension", "alimony", "investment"):
            with self.subTest(income_type=income_type):
                self.assert_eligible(self.calculate(self.household(head(30, {income_type: 300}), ("child", 7))), 125)

    def test_self_employment_gets_the_disregard(self):
        self.assert_eligible(self.calculate(self.household(head(30, {"selfEmployment": 400}), ("child", 7))), 225)

    def test_a_spouses_wages_count(self):
        screen = self.household(head(32), ("spouse", 31, {"wages": 400}), ("child", 8))

        self.assert_eligible(self.calculate(screen), 559 - 200)

    def test_a_childs_unearned_income_counts(self):
        screen = self.household(head(40), ("child", 16, {"sSDisability": 300}))

        self.assert_eligible(self.calculate(screen), 125)

    def test_cash_assistance_on_another_member_still_skips_schedule_i(self):
        screen = self.household(head(30, {"wages": 700}), ("spouse", 30, {"cashAssistance": 75}), ("child", 6))

        self.assert_eligible(self.calculate(screen), 559 - 350)


class TestScenarios(NjTanfTestCase):
    """One test per spec scenario. The spec numbers skip 12 and 22-24."""

    def test_scenario_01_parent_and_young_child_with_no_income(self):
        self.assert_eligible(self.calculate(self.household(head(), ("child", 5))), 425)

    def test_scenario_02_family_of_three_at_the_schedule_i_limit(self):
        screen = self.household(head(30, {"wages": 839}), ("child", 6), ("child", 3))

        self.assert_eligible(self.calculate(screen), "139.50")

    def test_scenario_03_family_of_three_one_dollar_over_schedule_i(self):
        screen = self.household(head(30, {"wages": 840}), ("child", 6), ("child", 3))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_04_family_of_four_at_its_schedule_i_limit(self):
        screen = self.household(head(32, {"wages": 966}), ("spouse", 31), ("child", 8), ("child", 4))

        self.assert_eligible(self.calculate(screen), 161)

    def test_scenario_05_family_of_four_one_dollar_over_its_schedule_i_limit(self):
        screen = self.household(head(32, {"wages": 967}), ("spouse", 31), ("child", 8), ("child", 4))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_06_parent_and_child_with_unemployment_benefits(self):
        screen = self.household(head(28, {"unemployment": 300}), ("child", 7))

        self.assert_eligible(self.calculate(screen), 125)

    def test_scenario_07_parent_on_ssi_with_a_child(self):
        screen = self.household(head(35, {"sSI": 994}), ("child", 9))

        self.assertEqual(self.unit_size(screen), 1)
        self.assert_eligible(self.calculate(screen), 214)

    def test_scenario_08_only_child_receives_ssi(self):
        screen = self.household(head(40), ("child", 10, {"sSI": 994}))

        self.assertEqual(self.unit_size(screen), 1)
        self.assert_eligible(self.calculate(screen), 214)

    def test_scenario_09_resources_exactly_at_2000(self):
        self.assert_eligible(self.calculate(self.household(head(), ("child", 5), assets=2_000)), 425)

    def test_scenario_10_resources_one_dollar_over_2000(self):
        self.assert_ineligible(self.calculate(self.household(head(), ("child", 5), assets=2_001)))

    def test_scenario_11_pregnant_woman_with_no_other_children(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, HEAD, 24, pregnant=True)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_13_only_child_is_an_18_year_old_not_in_school(self):
        self.assert_eligible(self.calculate(self.household(head(45), ("child", 18))), 425)

    def test_scenario_14_only_child_is_19_and_in_special_education(self):
        self.assert_ineligible(self.calculate(self.household(head(50), ("child", 19))))

    def test_scenario_15_only_child_is_unrelated_to_the_caretaker(self):
        self.assert_ineligible(self.calculate(self.household(head(38), ("roommate", 12))))

    def test_scenario_16_unearned_income_one_dollar_under_the_grant(self):
        self.assert_eligible(self.calculate(self.household(head(28, {"unemployment": 424}), ("child", 7))), 1)

    def test_scenario_17_ssi_parent_with_wages_and_a_child(self):
        screen = self.household(head(35, {"sSI": 994, "wages": 400}), ("child", 9))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_18_current_recipient_reports_their_own_wfnj_grant(self):
        screen = self.household(head(28, {"cashAssistance": 425}), ("child", 7))

        self.assert_eligible(self.calculate(screen), 425)

    def test_scenario_19_unearned_income_equal_to_the_grant(self):
        self.assert_ineligible(self.calculate(self.household(head(28, {"unemployment": 425}), ("child", 7))))

    def test_scenario_20_grandmother_with_wages_raising_her_grandchild(self):
        screen = self.household(head(60, {"wages": 3_000}), ("grandChild", 8))

        self.assertEqual(self.unit_size(screen), 1)
        self.assert_eligible(self.calculate(screen), 214)

    def test_scenario_21_parent_pays_child_support_out_of_unemployment(self):
        screen = self.household(head(30, {"unemployment": 700}), ("child", 6), child_support_paid=300)

        self.assert_eligible(self.calculate(screen), 25)

    def test_scenario_25_mother_and_baby_living_with_her_working_mother(self):
        screen = self.household(head(25), ("child", 1), ("parent", 50, {"wages": 1_500}))

        self.assertEqual(self.unit_size(screen), 2)
        self.assert_eligible(self.calculate(screen), 425)

    def test_scenario_26_current_recipient_with_wages(self):
        screen = self.household(head(30, {"wages": 700, "cashAssistance": 75}), ("child", 6))

        self.assert_eligible(self.calculate(screen), 75)

    def test_scenario_27_applicant_with_the_same_wages(self):
        self.assert_ineligible(self.calculate(self.household(head(30, {"wages": 700}), ("child", 6))))

    def test_scenario_28_parent_receiving_300_child_support_for_one_child(self):
        screen = self.household(head(30, {"childSupport": 300}), ("child", 4))

        self.assert_eligible(self.calculate(screen), 225)

    def test_scenario_29_parent_receiving_600_child_support_for_one_child(self):
        self.assert_ineligible(self.calculate(self.household(head(30, {"childSupport": 600}), ("child", 4))))

    def test_scenario_30_parent_on_unemployment_with_a_working_16_year_old(self):
        screen = self.household(head(40, {"unemployment": 300}), ("child", 16, {"wages": 400}))

        self.assert_eligible(self.calculate(screen), 125)

    def test_scenario_31_current_recipient_with_unemployment_and_wages(self):
        screen = self.household(head(30, {"unemployment": 300, "wages": 300, "cashAssistance": 50}), ("child", 6))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_32_parent_and_seven_children_at_the_eight_person_schedule_i_limit(self):
        children = [("child", age) for age in (15, 13, 11, 9, 7, 5, 3)]
        screen = self.household(head(38, {"wages": 1_442}), *children)

        self.assertEqual(self.unit_size(screen), 8)
        self.assert_eligible(self.calculate(screen), 240)

    def test_scenario_33_wages_and_unemployment_at_the_schedule_ii_level(self):
        screen = self.household(head(30, {"wages": 200, "unemployment": 325}), ("child", 6))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_34_wages_and_unemployment_one_dollar_under_the_schedule_ii_level(self):
        screen = self.household(head(30, {"wages": 200, "unemployment": 324}), ("child", 6))

        self.assert_eligible(self.calculate(screen), 1)

    def test_scenario_35_an_18_year_old_living_alone(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, HEAD, 18, pregnant=False)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_36_child_support_paid_exceeds_income(self):
        screen = self.household(head(30, {"unemployment": 200}), ("child", 6), child_support_paid=300)

        self.assert_eligible(self.calculate(screen), 425)

    def test_scenario_37_parent_on_unemployment_with_a_working_17_year_old(self):
        screen = self.household(head(40, {"unemployment": 300}), ("child", 17, {"wages": 400}))

        self.assert_eligible(self.calculate(screen), 125)

    def test_scenario_38_parent_on_unemployment_with_a_working_18_year_old(self):
        screen = self.household(head(40, {"unemployment": 300}), ("child", 18, {"wages": 400}))

        self.assert_eligible(self.calculate(screen), 125)

    def test_scenario_39_parent_receiving_300_child_support_for_two_children(self):
        screen = self.household(head(30, {"childSupport": 300}), ("child", 6), ("child", 3))

        self.assert_eligible(self.calculate(screen), 459)

    def test_scenario_40_parent_receiving_child_support_below_the_pass_through(self):
        self.assert_eligible(self.calculate(self.household(head(30, {"childSupport": 80}), ("child", 4))), 425)

    def test_scenario_41_applicant_with_wages_and_child_support_at_the_initial_test(self):
        screen = self.household(head(30, {"wages": 500, "childSupport": 200}), ("child", 4))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_42_grandmother_as_head_with_a_grandchild_no_income(self):
        screen = self.household(head(60), ("grandChild", 6))

        self.assertEqual(self.unit_size(screen), 1)
        self.assert_eligible(self.calculate(screen), 214)

    def test_scenario_43_grandmother_entered_as_head_with_her_adult_daughter_and_grandchild(self):
        screen = self.household(head(50, {"wages": 1_500}), ("child", 25), ("grandChild", 1))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_44_parent_and_child_with_a_working_domestic_partner(self):
        screen = self.household(head(30), ("child", 5), ("domesticPartner", 32, {"wages": 1_500}))

        self.assertEqual(self.unit_size(screen), 2)
        self.assert_eligible(self.calculate(screen), 425)

    def test_scenario_45_family_of_three_with_unemployment_one_dollar_under_the_grant(self):
        screen = self.household(head(32, {"unemployment": 558}), ("child", 8), ("child", 4))

        self.assert_eligible(self.calculate(screen), 1)

    def test_scenario_46_family_of_three_with_unemployment_equal_to_the_grant(self):
        screen = self.household(head(32, {"unemployment": 559}), ("child", 8), ("child", 4))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_47_parent_and_seven_children_one_dollar_over_the_eight_person_schedule_i_limit(self):
        children = [("child", age) for age in (15, 13, 11, 9, 7, 5, 3)]
        screen = self.household(head(38, {"wages": 1_443}), *children)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_48_ssi_parent_with_low_wages_and_a_child(self):
        screen = self.household(head(35, {"sSI": 994, "wages": 200}), ("child", 9))

        self.assert_eligible(self.calculate(screen), 14)

    def test_scenario_49_ssi_spouse_with_wages_head_with_no_income_and_a_child(self):
        screen = self.household(head(32), ("spouse", 33, {"sSI": 994, "wages": 300}), ("child", 5))

        self.assertEqual(self.unit_size(screen), 2)
        self.assert_eligible(self.calculate(screen), 125)

    def test_scenario_50_head_with_a_stepchild_and_no_income(self):
        screen = self.household(head(34), ("stepChild", 8))

        self.assertEqual(self.unit_size(screen), 2)
        self.assert_eligible(self.calculate(screen), 425)

    def test_scenario_51_grandmother_with_wages_and_child_support_reported_under_her(self):
        screen = self.household(head(60, {"wages": 3_000, "childSupport": 600}), ("grandChild", 6))

        self.assert_ineligible(self.calculate(screen))
