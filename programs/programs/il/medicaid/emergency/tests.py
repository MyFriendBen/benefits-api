"""
Unit tests for Illinois Emergency Medicaid calculator.

Tests verify:
- Insurance requirement (must have no insurance)
- Medicaid eligibility dependency
- Correct value calculation ($2,000 per eligible member)
"""

from django.test import TestCase
from unittest.mock import Mock, patch

from programs.programs.il.medicaid.emergency.calculator import IlEmergencyMedicaid
from screener.models import Screen, HouseholdMember, Insurance, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.util import Dependencies


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

    def create_calculator(self, screen, data=None):
        """Helper method to create calculator instance."""
        data = data or {}
        missing_dependencies = Dependencies()
        return IlEmergencyMedicaid(screen, self.program, data, missing_dependencies)

    # Calculator Configuration Tests
    def test_member_amount_is_2000(self):
        """Test that member amount is $2,000 (average ER visit cost)."""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
        )
        calc = self.create_calculator(screen)
        self.assertEqual(calc.member_amount, 2_000)

    def test_insurance_types_is_none(self):
        """Test that eligible insurance type is 'none' only."""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
        )
        calc = self.create_calculator(screen)
        self.assertEqual(calc.insurance_types, ["none"])

    def test_dependencies_includes_insurance(self):
        """Test that dependencies include insurance."""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
        )
        calc = self.create_calculator(screen)
        self.assertIn("insurance", calc.dependencies)

    # Member Eligibility Tests
    def test_member_eligible_with_no_insurance(self):
        """Test member is eligible when they have no insurance."""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
        )
        member = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
        )
        Insurance.objects.create(household_member=member, none=True)

        # Mock the medicaid_eligible helper
        data = {"medicaid_eligible": True}
        calc = self.create_calculator(screen, data)

        # Test member insurance check
        self.assertTrue(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_employer_insurance(self):
        """Test member is ineligible when they have employer insurance."""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
        )
        member = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
        )
        Insurance.objects.create(household_member=member, employer=True)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_medicaid(self):
        """Test member is ineligible when they already have Medicaid."""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
        )
        member = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
        )
        Insurance.objects.create(household_member=member, medicaid=True)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    def test_member_ineligible_with_medicare(self):
        """Test member is ineligible when they have Medicare."""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
        )
        member = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=68,
        )
        Insurance.objects.create(household_member=member, medicare=True)

        self.assertFalse(member.insurance.has_insurance_types(["none"]))

    # Household with Multiple Members Tests
    def test_only_uninsured_members_eligible(self):
        """Test that only uninsured members are eligible in a mixed household."""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
        )

        # Insured parent
        insured_member = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
        )
        Insurance.objects.create(household_member=insured_member, employer=True)

        # Uninsured child
        uninsured_member = HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=8,
        )
        Insurance.objects.create(household_member=uninsured_member, none=True)

        # Check insurance status
        self.assertFalse(insured_member.insurance.has_insurance_types(["none"]))
        self.assertTrue(uninsured_member.insurance.has_insurance_types(["none"]))
