from django.test import TestCase
from programs.programs.ma.cha.calculator import Cha
from screener.models import Screen, HouseholdMember, IncomeStream, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.util import Dependencies
from unittest.mock import patch, MagicMock


class TestCha(TestCase):
    """Test cases for Cambridge Housing Authority calculator"""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        cls.ma_white_label = WhiteLabel.objects.create(name="Massachusetts", code="ma", state_code="MA")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")
        cls.program = Program.objects.new_program(white_label="ma", name_abbreviated="ma_cha")
        cls.program.year = cls.fpl_year
        cls.program.save()

    def setUp(self):
        """Set up test fixtures for each test method"""
        self.eligible_screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="02138",
            county="Cambridge",
            household_size=2,
            white_label=self.ma_white_label,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(
            screen=self.eligible_screen,
            relationship="headOfHousehold",
            age=35,
            student=False,
            has_income=True,
        )

        # Income below 50% AMI (approx $50,000/year for 2-person household)
        IncomeStream.objects.create(
            screen=self.eligible_screen,
            household_member=self.head,
            type="wages",
            amount=3000,  # $36,000/year
            frequency="monthly",
        )

    def create_calculator(self, screen):
        """Helper method to create calculator instance"""
        data = {}
        missing_dependencies = Dependencies()
        return Cha(screen, self.program, data, missing_dependencies)

    @patch("programs.programs.ma.cha.calculator.hud_client")
    def test_household_eligible_in_cambridge_below_income_limit(self, mock_hud_client):
        """Test household is eligible when in Cambridge and below 50% AMI"""
        mock_hud_client.get_screen_il_ami.return_value = 50000  # 50% AMI limit

        calc = self.create_calculator(self.eligible_screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)
        mock_hud_client.get_screen_il_ami.assert_called_once_with(self.eligible_screen, "50%", "2025")

    @patch("programs.programs.ma.cha.calculator.hud_client")
    def test_household_ineligible_outside_cambridge(self, mock_hud_client):
        """Test household is ineligible when not in Cambridge"""
        mock_hud_client.get_screen_il_ami.return_value = 50000

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="02101",
            county="Boston",
            household_size=2,
            white_label=self.ma_white_label,
            completed=False,
        )
        head = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=head,
            type="wages",
            amount=3000,
            frequency="monthly",
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.cha.calculator.hud_client")
    def test_household_ineligible_income_too_high(self, mock_hud_client):
        """Test household is ineligible when income exceeds 50% AMI"""
        mock_hud_client.get_screen_il_ami.return_value = 50000

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="02138",
            county="Cambridge",
            household_size=2,
            white_label=self.ma_white_label,
            completed=False,
        )
        head = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
            has_income=True,
        )
        # Income above 50% AMI
        IncomeStream.objects.create(
            screen=screen,
            household_member=head,
            type="wages",
            amount=5000,  # $60,000/year - above limit
            frequency="monthly",
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.cha.calculator.hud_client")
    def test_household_eligible_income_at_limit(self, mock_hud_client):
        """Test household is eligible when income equals 50% AMI exactly"""
        mock_hud_client.get_screen_il_ami.return_value = 36000  # Set limit to match income

        calc = self.create_calculator(self.eligible_screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.cha.calculator.hud_client")
    def test_value_returns_one(self, mock_hud_client):
        """Test that value returns 1 for eligible households (displays as 'Varies')"""
        mock_hud_client.get_screen_il_ami.return_value = 50000

        calc = self.create_calculator(self.eligible_screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 1)

    @patch("programs.programs.ma.cha.calculator.hud_client")
    def test_eligibility_messages_on_failure(self, mock_hud_client):
        """Test that appropriate failure messages are added"""
        mock_hud_client.get_screen_il_ami.return_value = 30000  # Low limit

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="02101",
            county="Boston",  # Wrong location
            household_size=2,
            white_label=self.ma_white_label,
            completed=False,
        )
        head = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=35,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=head,
            type="wages",
            amount=3000,
            frequency="monthly",
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)
        # Should have failure messages for location and possibly income
        self.assertTrue(len(eligibility.fail_messages) >= 1)

    @patch("programs.programs.ma.cha.calculator.hud_client")
    def test_larger_household_size(self, mock_hud_client):
        """Test eligibility with larger household size"""
        mock_hud_client.get_screen_il_ami.return_value = 70000  # Higher limit for larger household

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="02139",
            county="Cambridge",
            household_size=5,
            white_label=self.ma_white_label,
            completed=False,
        )
        head = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=40,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=head,
            type="wages",
            amount=4000,  # $48,000/year
            frequency="monthly",
        )
        # Add children
        for age in [5, 8, 12, 15]:
            HouseholdMember.objects.create(
                screen=screen,
                relationship="child",
                age=age,
                has_income=False,
            )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)
