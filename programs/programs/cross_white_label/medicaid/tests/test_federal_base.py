"""The federal Medicaid base: which inputs it sends PolicyEngine, and how it values PolicyEngine's eligible members.

Each input's own behavior is tested in ``programs/framework/pe_dependencies/tests/test_federal_medicaid_inputs.py``;
the state scenarios that run it end to end are in each state's tests (``test_nj.py``).
"""

from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.framework.base import MemberEligibility

import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.federal_base import MAGI_INCOME_INPUTS, FederalMedicaid


class StandInState(FederalMedicaid, abstract=True):
    pass


class StandInPricedState(FederalMedicaid, abstract=True):
    group_spend_per_fye_enrollee = {
        "child": 4_203,
        "new_adult": 7_248,
        "other_adult": 7_351,
        "disabled": 38_688,
        "aged": 28_650,
    }


class TestFederalMedicaidInputs(SimpleTestCase):
    """The spec's rules that reach PolicyEngine through what is sent."""

    def test_magi_income_counts_boarders_and_all_alimony_and_leaves_out_va_benefits(self) -> None:
        self.assertIn(dependency.member.RentalAndBoarderIncomeDependency, MAGI_INCOME_INPUTS)
        self.assertIn(dependency.member.TaxableAlimonyIncomeDependency, MAGI_INCOME_INPUTS)
        self.assertIn(dependency.member.PensionIncomeWithoutVeteranDependency, MAGI_INCOME_INPUTS)
        self.assertNotIn(dependency.member.PensionIncomeDependency, MAGI_INCOME_INPUTS)
        for income_input in MAGI_INCOME_INPUTS:
            self.assertIn(income_input, FederalMedicaid.pe_inputs)

    def test_reported_medicare_is_sent(self) -> None:
        self.assertIn(dependency.member.IsMedicareEligibleDependency, FederalMedicaid.pe_inputs)

    def test_disability_comes_only_from_the_members_own_ssdi(self) -> None:
        self.assertIn(dependency.member.OwnSsdiDisabilityDependency, FederalMedicaid.pe_inputs)
        self.assertIn(dependency.member.OwnSsdiNotEngagedInSgaDependency, FederalMedicaid.pe_inputs)
        for checkbox_input in (
            dependency.member.IsDisabledDependency,
            dependency.member.MeetsSsiDisabilityCriteriaDependency,
            dependency.member.IsBlindDependency,
        ):
            self.assertNotIn(checkbox_input, FederalMedicaid.pe_inputs)

    def test_ssi_is_taken_up_only_from_the_members_own_ssi_income(self) -> None:
        self.assertIn(dependency.member.TakesUpOwnReportedSsiDependency, FederalMedicaid.pe_inputs)
        self.assertNotIn(dependency.member.TakesUpSsiIfEligibleDependency, FederalMedicaid.pe_inputs)

    def test_foster_status_is_not_sent(self) -> None:
        self.assertNotIn(dependency.member.FosterCareDependency, FederalMedicaid.pe_inputs)

    def test_state_location_is_left_to_the_state(self) -> None:
        for location_input in FederalMedicaid.pe_inputs:
            self.assertFalse(issubclass(location_input, dependency.household.StateCode))
            self.assertFalse(issubclass(location_input, dependency.household.CountyDependency))

    def test_is_separate_from_the_current_base(self) -> None:
        self.assertFalse(issubclass(FederalMedicaid, Medicaid))


class TestFederalMedicaidValue(SimpleTestCase):
    """PolicyEngine decides eligibility; the value is §7's figure for the member's spending group."""

    def calculator(self, pe_value: float, category: str) -> StandInPricedState:
        calculator = StandInPricedState.__new__(StandInPricedState)
        calculator.get_member_variable = Mock(return_value=pe_value)
        calculator.get_member_dependency_value = Mock(return_value=category)
        return calculator

    def member(self, age: int, pregnant: bool = False) -> Mock:
        return Mock(id=7, pregnant=pregnant, calc_age=Mock(return_value=age))

    def member_eligibility(self, pe_value: float, category: str, age: int) -> MemberEligibility:
        e = MemberEligibility(self.member(age))
        self.calculator(pe_value, category).member_eligible(e)
        return e

    def test_asks_policyengine_for_eligibility_and_category(self) -> None:
        self.assertEqual(FederalMedicaid.pe_name, "medicaid")
        self.assertEqual(FederalMedicaid.pe_outputs, [dependency.member.Medicaid, dependency.member.MedicaidCategory])

    def test_member_policyengine_turns_away_is_ineligible_and_valued_at_nothing(self) -> None:
        e = self.member_eligibility(0, "ADULT", 30)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_value_ignores_policyengines_amount(self) -> None:
        e = self.member_eligibility(12_919.58, "ADULT", 30)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 604 * 12)

    def test_each_member_rounds_to_the_nearest_dollar_half_up_before_annualising(self) -> None:
        # $4,203 ÷ 12 = $350.25 → $350; $28,650 ÷ 12 = $2,387.50 → $2,388.
        self.assertEqual(self.calculator(1, "OLDER_CHILD").member_value(self.member(10)), 350 * 12)
        self.assertEqual(self.calculator(1, "SENIOR_OR_DISABLED").member_value(self.member(70)), 2_388 * 12)

    def test_spending_groups_by_category(self) -> None:
        cases = [
            ("INFANT", 0, 350),
            ("YOUNG_CHILD", 4, 350),
            ("OLDER_CHILD", 12, 350),
            ("ADULT", 40, 604),
            ("PREGNANT", 25, 613),
            ("PARENT", 18, 350),
            ("PARENT", 19, 613),
            ("SSI_RECIPIENT", 64, 3_224),
            ("SSI_RECIPIENT", 65, 2_388),
            ("SENIOR_OR_DISABLED", 50, 3_224),
        ]
        for category, age, monthly in cases:
            with self.subTest(category=category, age=age):
                e = self.member_eligibility(1, category, age)
                self.assertTrue(e.eligible)
                self.assertEqual(e.value, monthly * 12)

    def test_every_eligible_member_has_a_value_above_zero(self) -> None:
        # The screener hides a program whose value is $0, so an eligible member at $0 would never
        # be seen. Unknown age falls to the adult and disabled groups.
        for category in FederalMedicaid.covered_categories:
            for age in (None, 0, 18, 19, 64, 65, 90):
                with self.subTest(category=category, age=age):
                    e = self.member_eligibility(1, category, age)
                    self.assertTrue(e.eligible)
                    self.assertGreater(e.value, 0)

    def test_category_outside_the_specs_routes_is_ineligible(self) -> None:
        # §3's routes include none of these; NJ records medically needy and WorkAbility as
        # pathways MFB does not screen (decisions.md 7 and 13).
        for category in ("MEDICALLY_NEEDY", "YOUNG_ADULT", "WORKING_DISABLED_BUY_IN", "SECTION_1115_MEC_ADULT", "NONE"):
            with self.subTest(category=category):
                e = self.member_eligibility(1, category, 40)
                self.assertFalse(e.eligible)
                self.assertEqual(e.value, 0)

    def test_household_eligibility_comes_from_the_members_not_the_value(self) -> None:
        calculator = self.calculator(1, "ADULT")
        calculator.screen = Mock(household_members=Mock(all=Mock(return_value=[self.member(30)])))
        calculator.get_variable = Mock(return_value=0)
        e = calculator.eligible()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 604 * 12)

        calculator = self.calculator(0, "ADULT")
        calculator.screen = Mock(household_members=Mock(all=Mock(return_value=[self.member(30)])))
        self.assertFalse(calculator.eligible().eligible)

    def test_state_must_price_every_group_it_can_reach(self) -> None:
        class Unpriced(FederalMedicaid, abstract=True):
            group_spend_per_fye_enrollee = {"child": 4_203}

        with self.assertRaises(ValueError):
            Unpriced.check_every_reachable_group_is_priced()
        StandInPricedState.check_every_reachable_group_is_priced()

    def test_abstract_base_need_not_price(self) -> None:
        self.assertEqual(StandInState.annual_value_by_group, {})

    def test_unknown_spending_group_is_refused(self) -> None:
        with self.assertRaises(ValueError):

            class Bad(FederalMedicaid, abstract=True):
                group_spend_per_fye_enrollee = {"teen": 1}

    def test_category_mapped_to_unknown_group_is_refused(self) -> None:
        with self.assertRaises(ValueError):

            class Misspelled(FederalMedicaid, abstract=True):
                category_groups = {**FederalMedicaid.category_groups, "ADULT": "new-adult"}

    def test_covered_category_without_a_group_is_refused(self) -> None:
        with self.assertRaises(ValueError):

            class Uncovered(FederalMedicaid, abstract=True):
                covered_categories = (*FederalMedicaid.covered_categories, "MEDICALLY_NEEDY")
