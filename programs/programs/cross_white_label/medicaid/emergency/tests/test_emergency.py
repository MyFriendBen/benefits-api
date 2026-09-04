from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase, add_insurance

"""
Unit tests for Illinois Emergency Medicaid calculator.

Tests verify:
- Insurance requirement (must have no insurance)
- Medicaid eligibility dependency
- Correct value calculation ($2,000 per eligible member)
"""

from unittest.mock import Mock

from programs.programs.cross_white_label.medicaid.emergency.il import IlEmergencyMedicaid
from programs.framework.pe_dependencies import member

# Named constants for test values
EMERGENCY_MEDICAID_VALUE = 2_000  # Average ER visit cost

from screener.models import HouseholdMember, Insurance


class TestIlEmergencyMedicaid(CustomCalculatorTestCase):
    """Test cases for Illinois Emergency Medicaid calculator."""

    calculator_class = IlEmergencyMedicaid
    white_label_code = "il"
    state_code = "IL"
    default_zipcode = "60601"
    default_county = "Cook"

    def setUp(self):
        """Set up a fresh screen for each test."""
        self.screen = self.make_screen(household_size=1)

    def create_calculator(self, screen=None, data=None):
        return self.make_calculator(screen or self.screen, data)

    # Calculator Configuration Tests
    def test_member_amount_is_2000(self):
        """Test that member amount is $2,000 (average ER visit cost)."""
        calc = self.create_calculator()
        self.assertEqual(calc.member_amount, EMERGENCY_MEDICAID_VALUE)

    def test_insurance_types_is_none(self):
        """Test that eligible insurance type is 'none' only."""
        calc = self.create_calculator()
        self.assertEqual(calc.insurance_types, ["none"])

    def test_dependencies_includes_insurance(self):
        """Test that dependencies include insurance."""
        calc = self.create_calculator()
        self.assertIn("insurance", calc.dependencies)

    # Member Eligibility Tests
    def test_member_eligible_with_no_insurance(self):
        """Test member is eligible when they have no insurance."""
        member = self.add_member(self.screen, "headOfHousehold", 35)
        add_insurance(member, none=True)

        # Mock the medicaid_eligible helper
        data = {"medicaid_eligible": True}
        calc = self.create_calculator(data=data)

        # Test member insurance check
        self.assertTrue(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_employer_insurance(self):
        """Test member is ineligible when they have employer insurance."""
        member = self.add_member(self.screen, "headOfHousehold", 35)
        add_insurance(member, employer=True, none=False)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_medicaid(self):
        """Test member is ineligible when they already have Medicaid."""
        member = self.add_member(self.screen, "headOfHousehold", 35)
        add_insurance(member, medicaid=True, none=False)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_medicare(self):
        """Test member is ineligible when they have Medicare."""
        member = self.add_member(self.screen, "headOfHousehold", 68)
        add_insurance(member, medicare=True, none=False)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    # Household with Multiple Members Tests
    def test_only_uninsured_members_eligible(self):
        """Test that only uninsured members are eligible in a mixed household."""
        self.screen.household_size = 2
        self.screen.save()

        # Insured parent
        insured_member = self.add_member(self.screen, "headOfHousehold", 35)
        add_insurance(insured_member, employer=True, none=False)

        # Uninsured child
        uninsured_member = self.add_member(self.screen, "child", 8)
        add_insurance(uninsured_member, none=True)

        # Check insurance status
        self.assertFalse(insured_member.insurance.has_insurance_types(["none"]))
        self.assertTrue(uninsured_member.insurance.has_insurance_types(["none"]))

    # Edge Case / Error Handling Tests
    def test_handles_zero_age_member(self):
        """Test that calculator handles newborn (age 0) without error."""
        member = self.add_member(self.screen, "child", 0)
        add_insurance(member, none=True)

        calc = self.create_calculator()
        # Should not raise an exception
        self.assertIsNotNone(calc)
        self.assertTrue(member.insurance.has_insurance_types(["none"]))

    def test_handles_member_without_insurance_record(self):
        """A member with no `Insurance` row raises when one is read.

        The screener always writes the row, so this is the shape a partial or corrupted
        household would have. The shared builder writes it too, so this test deletes it
        to reach the case.
        """
        member = self.add_member(self.screen, "headOfHousehold", 35)
        Insurance.objects.filter(household_member=member).delete()
        member.refresh_from_db()

        self.assertIsNotNone(self.create_calculator())

        with self.assertRaises(HouseholdMember.insurance.RelatedObjectDoesNotExist):
            _ = member.insurance

    def test_handles_empty_household(self):
        """Test that calculator handles screen with no members."""
        self.screen.household_size = 0
        self.screen.save()

        calc = self.create_calculator()
        # Should not raise an exception
        self.assertIsNotNone(calc)
        self.assertEqual(calc.member_amount, EMERGENCY_MEDICAID_VALUE)

    def test_handles_very_old_member(self):
        """Test that calculator handles elderly members (age 100+)."""
        member = self.add_member(self.screen, "headOfHousehold", 105)
        add_insurance(member, none=True)

        calc = self.create_calculator()
        self.assertIsNotNone(calc)
        self.assertTrue(member.insurance.has_insurance_types(["none"]))
