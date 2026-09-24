"""
Unit tests for MaHomeBridge calculator class.

These tests verify the HomeBridge calculator logic for Cambridge's first-time
homebuyer assistance program, including:
- Calculator registration
- Cambridge residency eligibility
- Income eligibility (60%-120% AMI)
- Dependencies configuration
"""

from django.test import TestCase
from unittest.mock import Mock, patch

from programs.programs.testing_fixtures.custom_calculator import hud_ami
from programs.programs.white_labels.ma.homebridge.calculator import MaHomeBridge
from programs.framework.base import ProgramCalculator, Eligibility


class TestMaHomeBridgeCalculator(TestCase):
    """Tests for MaHomeBridge calculator class."""

    def test_exists_and_is_subclass_of_program_calculator(self):
        """Test that MaHomeBridge calculator class exists and inherits correctly."""
        self.assertTrue(issubclass(MaHomeBridge, ProgramCalculator))

    def test_eligible_city_is_cambridge(self):
        """Test that the eligible city is set to Cambridge."""
        self.assertEqual(MaHomeBridge.eligible_city, "Cambridge")

    def test_hud_county_is_middlesex(self):
        """Test that the HUD county is Middlesex (Cambridge is in Middlesex County)."""
        self.assertEqual(MaHomeBridge.hud_county, "Middlesex")

    def test_ami_max_multiplier_is_correct(self):
        """Test that ami_max_multiplier is 1.5 (80% AMI × 1.5 = 120% AMI)."""
        self.assertEqual(MaHomeBridge.ami_max_multiplier, 1.5)

    def test_dependencies_are_defined(self):
        """Test that required dependencies are properly defined."""
        expected_deps = ["zipcode", "income_amount", "income_frequency", "household_size"]
        self.assertEqual(list(MaHomeBridge.dependencies), expected_deps)


class TestMaHomeBridgeLocationEligibility(TestCase):
    """Tests for Cambridge location eligibility check."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_program.year = Mock()
        self.mock_program.year.as_dict.return_value = {1: 15000, 2: 20000, 3: 25000, 4: 30000}
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, county, household_size=4, income=60000, has_benefit=False):
        """Helper to create a calculator with mocked screen."""
        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.household_size = household_size
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaHomeBridge(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_cambridge_resident_passes_location_check(self):
        """Test that Cambridge residents pass the location eligibility check."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):

            calculator = self._create_calculator("Cambridge", income=70000)
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            # Should be eligible (location passes, income in range)
            self.assertTrue(eligibility.eligible)

    def test_non_cambridge_resident_fails_location_check(self):
        """Test that non-Cambridge residents fail the location eligibility check."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):

            calculator = self._create_calculator("Boston", income=70000)
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            # Should be ineligible (location fails)
            self.assertFalse(eligibility.eligible)

    def test_somerville_resident_fails_location_check(self):
        """Test that Somerville (adjacent to Cambridge) residents are not eligible."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):

            calculator = self._create_calculator("Somerville", income=70000)
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            self.assertFalse(eligibility.eligible)


class TestMaHomeBridgeIncomeEligibility(TestCase):
    """Tests for AMI-based income eligibility check."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, income, household_size=4, has_benefit=False):
        """Helper to create a calculator with specified income."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = household_size
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaHomeBridge(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_income_at_60_percent_ami_is_eligible(self):
        """Test that income exactly at 60% AMI is eligible."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):
            # 60% AMI = 60000, 80% AMI = 80000, so 120% AMI = 80000 x 1.5 = 120000

            calculator = self._create_calculator(income=60000)
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            self.assertTrue(eligibility.eligible)

    def test_income_at_120_percent_ami_is_eligible(self):
        """Test that income exactly at 120% AMI is eligible."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):
            # 60% AMI = 60000, 80% AMI = 80000, so 120% AMI = 80000 x 1.5 = 120000

            calculator = self._create_calculator(income=120000)
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            self.assertTrue(eligibility.eligible)

    def test_income_between_60_and_120_percent_ami_is_eligible(self):
        """Test that income between 60% and 120% AMI is eligible."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):
            # 60% AMI = 60000, 80% AMI = 80000, so 120% AMI = 120000; midpoint = 90000

            calculator = self._create_calculator(income=90000)
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            self.assertTrue(eligibility.eligible)

    def test_income_below_60_percent_ami_is_ineligible(self):
        """Test that income below 60% AMI is not eligible."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):
            # 60% AMI = 60000

            calculator = self._create_calculator(income=50000)  # Below 60% AMI
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            self.assertFalse(eligibility.eligible)

    def test_income_above_120_percent_ami_is_ineligible(self):
        """Test that income above 120% AMI is not eligible."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):
            # 80% AMI = 80000, so 120% AMI = 80000 x 1.5 = 120000

            calculator = self._create_calculator(income=130000)  # Above 120% AMI
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            self.assertFalse(eligibility.eligible)


class TestMaHomeBridgeHudApiError(TestCase):
    """Tests for HUD API error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, income=70000, has_benefit=False):
        """Helper to create a calculator."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 4
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaHomeBridge(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_hud_api_error_results_in_ineligibility(self):
        """Test that HUD API errors result in ineligibility (income cannot be verified)."""
        with hud_ami(MaHomeBridge, unavailable=True):
            calculator = self._create_calculator()
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            # Should be ineligible when AMI cannot be retrieved
            self.assertFalse(eligibility.eligible)


class TestMaHomeBridgeHasBenefit(TestCase):
    """Tests for has_benefit behavior - users who already have the benefit should be ineligible."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, has_benefit=False, income=70000):
        """Helper to create a calculator."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 4
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaHomeBridge(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_user_without_benefit_is_eligible(self):
        """Test that users who don't have the benefit can be eligible."""
        with hud_ami(MaHomeBridge, {"60%": 60000, "80%": 80000}):

            calculator = self._create_calculator(has_benefit=False, income=70000)
            eligibility = Eligibility()

            calculator.household_eligible(eligibility)

            self.assertTrue(eligibility.eligible)


class TestMaHomeBridgeValue(TestCase):
    """Tests for benefit value calculation."""

    def test_amount_is_one(self):
        """Test that amount is 1 (FE displays 'Varies' for low_confidence programs)."""
        self.assertEqual(MaHomeBridge.amount, 1)
