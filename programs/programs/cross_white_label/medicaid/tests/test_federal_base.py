"""The federal Medicaid base: which inputs it sends PolicyEngine, and that it takes PolicyEngine's answer as is.

Each input's own behavior is tested in ``programs/framework/pe_dependencies/tests/test_federal_medicaid_inputs.py``;
the state scenarios that run it end to end are in each state's tests (``test_nj.py``).
"""

from unittest.mock import Mock

from django.test import SimpleTestCase

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.federal_base import MAGI_INCOME_INPUTS, FederalMedicaid


class StandInState(FederalMedicaid, abstract=True):
    pass


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


class TestFederalMedicaidTakesPolicyEnginesAnswer(SimpleTestCase):
    """A pure PolicyEngine calculator: nothing is layered on PolicyEngine's answer."""

    def test_asks_policyengine_for_medicaid_only(self) -> None:
        self.assertEqual(FederalMedicaid.pe_name, "medicaid")
        self.assertEqual(FederalMedicaid.pe_outputs, [dependency.member.Medicaid])

    def test_member_value_is_policyengines_medicaid_value(self) -> None:
        self.assertIs(FederalMedicaid.member_value, PolicyEngineMembersCalculator.member_value)
        self.assertIs(FederalMedicaid.household_value, PolicyEngineMembersCalculator.household_value)

        calculator = StandInState.__new__(StandInState)
        calculator.get_member_variable = Mock(return_value=12_919.58)
        member = Mock(id=7)

        self.assertEqual(calculator.member_value(member), 12_919.58)
        calculator.get_member_variable.assert_called_once_with(7)
