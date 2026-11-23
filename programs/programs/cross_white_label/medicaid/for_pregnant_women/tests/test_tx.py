"""TX tests."""

from unittest.mock import MagicMock
from unittest.mock import Mock
from django.test import TestCase
from programs.programs.cross_white_label.medicaid.for_pregnant_women.tx import TxMedicaidForPregnantWomen


class TestTxMedicaidForPregnantWomen(TestCase):
    """Tests for TxMedicaidForPregnantWomen calculator class."""

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
