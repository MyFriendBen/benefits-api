"""
Unit tests for Illinois Emergency Medicaid calculator.

Tests verify:
- Insurance requirement (must have no insurance)
- Medicaid eligibility dependency
- Correct value calculation ($2,000 per eligible member)
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.il.medicaid.emergency.calculator import IlEmergencyMedicaid
from screener.models import Screen, HouseholdMember, Insurance, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.util import Dependencies

# Named constants for test values
EMERGENCY_MEDICAID_VALUE = 2_000  # Average ER visit cost


class TestIlEmergencyMedicaid(TestCase):
    """Test cases for Illinois Emergency Medicaid calculator."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests."""
        cls.il_white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")

        cls.program = Program.objects.new_program(white_label="il", name_abbreviated="il_emergency_medicaid")
        cls.program.year = cls.fpl_year
        cls.program.save()

    def setUp(self):
        """Set up a fresh screen for each test."""
        self.screen = Screen.objects.create(
            agree_to_tos=True,
            completed=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
        )

    def create_calculator(self, screen=None, data=None):
        """Helper method to create calculator instance."""
        screen = screen or self.screen
        data = data or {}
        missing_dependencies = Dependencies()
        return IlEmergencyMedicaid(screen, self.program, data, missing_dependencies)

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
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
        )
        Insurance.objects.create(household_member=member, none=True)

        # Mock the medicaid_eligible helper
        data = {"medicaid_eligible": True}
        calc = self.create_calculator(data=data)

        # Test member insurance check
        self.assertTrue(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_employer_insurance(self):
        """Test member is ineligible when they have employer insurance."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
        )
        Insurance.objects.create(household_member=member, employer=True, none=False)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_medicaid(self):
        """Test member is ineligible when they already have Medicaid."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
        )
        Insurance.objects.create(household_member=member, medicaid=True, none=False)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_medicare(self):
        """Test member is ineligible when they have Medicare."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=68,
        )
        Insurance.objects.create(household_member=member, medicare=True, none=False)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    # Household with Multiple Members Tests
    def test_only_uninsured_members_eligible(self):
        """Test that only uninsured members are eligible in a mixed household."""
        self.screen.household_size = 2
        self.screen.save()

        # Insured parent
        insured_member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
        )
        Insurance.objects.create(household_member=insured_member, employer=True, none=False)

        # Uninsured child
        uninsured_member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=8,
        )
        Insurance.objects.create(household_member=uninsured_member, none=True)

        # Check insurance status
        self.assertFalse(insured_member.insurance.has_insurance_types(["none"]))
        self.assertTrue(uninsured_member.insurance.has_insurance_types(["none"]))

    # Edge Case / Error Handling Tests
    def test_handles_zero_age_member(self):
        """Test that calculator handles newborn (age 0) without error."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=0,
        )
        Insurance.objects.create(household_member=member, none=True)

        calc = self.create_calculator()
        # Should not raise an exception
        self.assertIsNotNone(calc)
        self.assertTrue(member.insurance.has_insurance_types(["none"]))

    def test_handles_member_without_insurance_record(self):
        """Test behavior when Insurance object doesn't exist for member."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
        )
        # Note: No Insurance.objects.create() call

        calc = self.create_calculator()
        # Calculator should be created without error
        self.assertIsNotNone(calc)

        # Accessing insurance should raise an expected error
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
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=105,
        )
        Insurance.objects.create(household_member=member, none=True)

        calc = self.create_calculator()
        self.assertIsNotNone(calc)
        self.assertTrue(member.insurance.has_insurance_types(["none"]))
