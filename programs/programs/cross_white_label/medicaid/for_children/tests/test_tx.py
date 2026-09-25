"""TX tests."""

from unittest.mock import MagicMock
from unittest.mock import Mock
from django.test import TestCase
from programs.programs.cross_white_label.medicaid.for_children.tx import TxMedicaidForChildren


class TestTxMedicaidForChildren(TestCase):
    """Tests for TxMedicaidForChildren calculator class."""

    def test_member_value_returns_zero_for_adults_age_19_or_older(self):
        """
        Test that member_value returns 0 for members aged 19 or older.

        TX Medicaid for Children is only for children under 19.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the parent's member_value method
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member aged 19
        member = Mock()
        member.id = 1
        member.age = 19
        member.has_insurance_types = Mock(return_value=True)
        member.has_disability = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (too old)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_for_children_with_insurance(self):
        """
        Test that member_value returns 0 for children who have other insurance.

        TX Medicaid for Children requires that children do not have other health insurance.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member under 19 with insurance
        member = Mock()
        member.id = 1
        member.age = 10
        member.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False
        member.has_disability = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (has insurance)
        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_pe_value_for_eligible_children(self):
        """
        Test that member_value returns PolicyEngine value for eligible children.

        When a child is under 19 and has no insurance, the PolicyEngine-calculated
        Medicaid value should be returned directly.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 250
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member under 19 without insurance
        member = Mock()
        member.id = 1
        member.age = 12
        member.has_insurance_types = Mock(return_value=True)  # has_insurance_types(("none",)) returns True

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value directly
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_age_boundary_18_is_eligible(self):
        """
        Test that 18-year-olds are eligible for TX Medicaid for Children.

        The program covers children 18 and under, so 18 should be eligible.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 300
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member aged 18 without insurance
        member = Mock()
        member.id = 1
        member.age = 18
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value (18 is eligible)
        self.assertEqual(result, pe_value)

    def test_member_value_checks_age_before_insurance(self):
        """
        Test that age check happens before insurance check for efficiency.

        If a member is too old, we shouldn't need to check their insurance status.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock member aged 25
        member = Mock()
        member.id = 1
        member.age = 25
        member.has_insurance_types = Mock()  # Should not be called

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0
        self.assertEqual(result, 0)

        # Insurance check should not be called since age check fails first
        member.has_insurance_types.assert_not_called()

    def test_member_value_with_infant(self):
        """
        Test that member_value works correctly for infants (age 0).

        Infants should be eligible if they have no other insurance.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 400
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock infant without insurance
        member = Mock()
        member.id = 1
        member.age = 0
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value (infant is eligible)
        self.assertEqual(result, pe_value)
