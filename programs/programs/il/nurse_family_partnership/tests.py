"""
Unit tests for Illinois Nurse-Family Partnership (NFP) calculator.

Tests verify:
- Income eligibility (300% FPL or WIC presumed eligibility)
- Pregnancy requirement for member eligibility
- Correct value calculation ($6,000 / 2.5 years = $2,400/year)
"""

from django.test import TestCase
from programs.programs.il.nurse_family_partnership.calculator import IlNurseFamilyPartnership
from screener.models import Screen, HouseholdMember, IncomeStream, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.util import Dependencies


class TestIlNurseFamilyPartnership(TestCase):
    """Test cases for Illinois Nurse-Family Partnership calculator."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests."""
        cls.il_white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")

        cls.program = Program.objects.new_program(white_label="il", name_abbreviated="il_nfp")
        cls.program.year = cls.fpl_year
        cls.program.save()

    def setUp(self):
        """Set up test fixtures for each test method."""
        self.screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=1,
            white_label=self.il_white_label,
            completed=False,
        )

    def create_calculator(self, screen):
        """Helper method to create calculator instance."""
        data = {}
        missing_dependencies = Dependencies()
        return IlNurseFamilyPartnership(screen, self.program, data, missing_dependencies)

    # Household Eligibility Tests
    def test_household_eligible_income_below_300_fpl(self):
        """Test household is eligible when income is below 300% FPL."""
        parent = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            pregnant=True,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=parent,
            type="wages",
            amount=2500,
            frequency="monthly",
        )

        calc = self.create_calculator(self.screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_household_eligible_with_wic_regardless_of_income(self):
        """Test household is eligible with WIC (presumed eligibility) regardless of income."""
        self.screen.has_wic = True
        self.screen.save()

        parent = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=28,
            pregnant=True,
            has_income=True,
        )
        # Income above 300% FPL
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=parent,
            type="wages",
            amount=6000,
            frequency="monthly",
        )

        calc = self.create_calculator(self.screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_household_ineligible_income_above_300_fpl_no_wic(self):
        """Test household is ineligible when income exceeds 300% FPL and no WIC."""
        parent = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=30,
            pregnant=True,
            has_income=True,
        )
        # Income well above 300% FPL
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=parent,
            type="wages",
            amount=7000,
            frequency="monthly",
        )

        calc = self.create_calculator(self.screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    # Member Eligibility Tests
    def test_member_eligible_when_pregnant(self):
        """Test member is eligible when pregnant."""
        pregnant_member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            pregnant=True,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=pregnant_member,
            type="wages",
            amount=2000,
            frequency="monthly",
        )

        calc = self.create_calculator(self.screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 1)

    def test_member_ineligible_when_not_pregnant(self):
        """Test member is ineligible when not pregnant."""
        non_pregnant = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            pregnant=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=non_pregnant,
            type="wages",
            amount=2000,
            frequency="monthly",
        )

        calc = self.create_calculator(self.screen)
        eligibility = calc.eligible()

        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 0)

    def test_only_pregnant_member_eligible_in_household(self):
        """Test only pregnant members are eligible, not all household members."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=30,
            pregnant=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=head,
            type="wages",
            amount=2500,
            frequency="monthly",
        )

        pregnant_spouse = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="spouse",
            age=28,
            pregnant=True,
            has_income=False,
        )

        calc = self.create_calculator(self.screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 1)  # Only pregnant spouse

    # Value Tests
    def test_value_calculation(self):
        """Test that value is $6,000 / 2.5 years = $2,400/year."""
        calc = self.create_calculator(self.screen)
        expected_value = 6_000 / 2.5
        self.assertEqual(calc.amount, expected_value)

    def test_fpl_percent_is_300(self):
        """Test that FPL threshold is 300%."""
        calc = self.create_calculator(self.screen)
        self.assertEqual(calc.fpl_percent, 3)

    def test_zero_income_eligible(self):
        """Test that zero income household is eligible."""
        parent = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=22,
            pregnant=True,
            has_income=False,
        )

        calc = self.create_calculator(self.screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)
