"""The federal Medicaid base: which inputs it sends PolicyEngine, and how it values PolicyEngine's eligible members.

Each input's own behavior is tested in ``programs/framework/pe_dependencies/tests/test_federal_medicaid_inputs.py``;
the state scenarios that run it end to end are in each state's tests (``test_nj.py``).
"""

from unittest.mock import Mock

from django.test import SimpleTestCase

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

    def test_asks_policyengine_for_eligibility_and_category(self) -> None:
        self.assertEqual(FederalMedicaid.pe_name, "medicaid")
        self.assertEqual(FederalMedicaid.pe_outputs, [dependency.member.Medicaid, dependency.member.MedicaidCategory])

    def test_ineligible_member_is_valued_at_nothing(self) -> None:
        self.assertEqual(self.calculator(0, "ADULT").member_value(self.member(30)), 0)

    def test_value_ignores_policyengines_amount(self) -> None:
        self.assertEqual(self.calculator(12_919.58, "ADULT").member_value(self.member(30)), 604 * 12)

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
                self.assertEqual(self.calculator(1, category).member_value(self.member(age)), monthly * 12)

    def test_category_without_a_figure_is_valued_at_nothing(self) -> None:
        self.assertEqual(self.calculator(1, "MEDICALLY_NEEDY").member_value(self.member(40)), 0)

    def test_group_the_state_does_not_price_is_valued_at_nothing(self) -> None:
        calculator = StandInState.__new__(StandInState)
        calculator.get_member_variable = Mock(return_value=1)
        calculator.get_member_dependency_value = Mock(return_value="ADULT")
        self.assertEqual(calculator.member_value(self.member(40)), 0)

    def test_unknown_spending_group_is_refused(self) -> None:
        with self.assertRaises(ValueError):

            class Bad(FederalMedicaid, abstract=True):
                group_spend_per_fye_enrollee = {"teen": 1}
