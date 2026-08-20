"""TX tests."""

from unittest.mock import MagicMock
from programs.programs.cross_white_label.medicaid.base import Medicaid
from unittest.mock import Mock
from django.test import TestCase
from programs.programs.cross_white_label.medicaid.emergency.tx import TxEmergencyMedicaid
from programs.programs.cross_white_label.medicaid.for_pregnant_women.tx import TxMedicaidForPregnantWomen
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household
from programs.framework.pe_dependencies import member


class TestTxMedicaidForPregnantWomen(TestCase):
    """Tests for TxMedicaidForPregnantWomen calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxMedicaidForPregnantWomen calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxMedicaidForPregnantWomen is a subclass of Medicaid
        self.assertTrue(issubclass(TxMedicaidForPregnantWomen, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxMedicaidForPregnantWomen.pe_name, "medicaid")
        self.assertIsNotNone(TxMedicaidForPregnantWomen.pe_inputs)
        self.assertGreater(len(TxMedicaidForPregnantWomen.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxMedicaidForPregnantWomen has all expected pe_inputs from parent and TX-specific.

        TxMedicaidForPregnantWomen should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxMedicaidForPregnantWomen should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxMedicaidForPregnantWomen.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxMedicaidForPregnantWomen.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxMedicaidForPregnantWomen.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Medicaid inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxMedicaidForPregnantWomen.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxMedicaidForPregnantWomen has the same pe_outputs as parent Medicaid class."""
        # TxMedicaidForPregnantWomen should use the same outputs as parent
        self.assertEqual(TxMedicaidForPregnantWomen.pe_outputs, Medicaid.pe_outputs)

    def test_member_value_returns_zero_for_non_pregnant_members(self):
        """
        Test that member_value returns 0 for members who are not pregnant.

        TX Medicaid for Pregnant Women is only for pregnant individuals.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the parent's member_value method
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member who is not pregnant
        member = Mock()
        member.id = 1
        member.pregnant = False
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (not pregnant)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_for_pregnant_members_with_insurance(self):
        """
        Test that member_value returns 0 for pregnant members who have other insurance.

        TX Medicaid for Pregnant Women requires that pregnant persons do not have other health insurance.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock pregnant member with insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (has insurance)
        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_pe_value_for_eligible_pregnant_women(self):
        """
        Test that member_value returns PolicyEngine value for eligible pregnant women.

        When a member is pregnant and has no insurance, the PolicyEngine-calculated
        Medicaid value should be returned directly.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 350
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)  # has_insurance_types(("none",)) returns True

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value directly
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_checks_pregnancy_before_insurance(self):
        """
        Test that pregnancy check happens before insurance check for efficiency.

        If a member is not pregnant, we shouldn't need to check their insurance status.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock non-pregnant member
        member = Mock()
        member.id = 1
        member.pregnant = False
        member.has_insurance_types = Mock()  # Should not be called

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0
        self.assertEqual(result, 0)

        # Insurance check should not be called since pregnancy check fails first
        member.has_insurance_types.assert_not_called()

    def test_member_value_with_zero_pe_value_and_eligible_pregnant_woman(self):
        """
        Test that member_value returns 0 when PolicyEngine returns 0, even for eligible pregnant women.

        If PolicyEngine determines no benefit value, it should be returned as-is
        (the member may not be income-eligible even though they are pregnant and have no insurance).
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock zero PolicyEngine value
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (PE says not eligible based on income)
        self.assertEqual(result, 0)

    def test_member_value_with_high_pe_value_but_has_insurance(self):
        """
        Test that insurance eligibility check occurs regardless of PolicyEngine value.

        Even if PolicyEngine returns a high value, the insurance check should still
        determine the final eligibility.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock high PolicyEngine value
        calculator.get_member_variable = Mock(return_value=500)

        # Create a mock pregnant member with insurance (not eligible)
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 despite high PE value
        self.assertEqual(result, 0)

        # Verify insurance check was performed
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_calls_get_member_variable_with_member_id(self):
        """
        Test that member_value calls get_member_variable with the correct member ID.

        This verifies that the PolicyEngine value is fetched for the right member.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=200)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 99
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        calculator.member_value(member)

        # Verify get_member_variable was called with the correct member ID
        calculator.get_member_variable.assert_called_once_with(99)
