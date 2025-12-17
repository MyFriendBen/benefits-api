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
from unittest.mock import Mock, patch, MagicMock

from programs.programs.ma import ma_calculators
from programs.programs.ma.homebridge.calculator import MaHomeBridge
from programs.programs.calc import ProgramCalculator, Eligibility


class TestMaHomeBridgeCalculator(TestCase):
    """Tests for MaHomeBridge calculator class."""

    def test_exists_and_is_subclass_of_program_calculator(self):
        """Test that MaHomeBridge calculator class exists and inherits correctly."""
        self.assertTrue(issubclass(MaHomeBridge, ProgramCalculator))

    def test_is_registered_in_ma_calculators(self):
        """Test that HomeBridge is registered in the MA calculators dictionary."""
        self.assertIn("ma_homebridge", ma_calculators)
        self.assertEqual(ma_calculators["ma_homebridge"], MaHomeBridge)

    def test_eligible_city_is_cambridge(self):
        """Test that the eligible city is set to Cambridge."""
        self.assertEqual(MaHomeBridge.eligible_city, "Cambridge")

    def test_hud_county_is_middlesex(self):
        """Test that the HUD county is Middlesex (Cambridge is in Middlesex County)."""
        self.assertEqual(MaHomeBridge.hud_county, "Middlesex")

    def test_ami_thresholds_are_correct(self):
        """Test that AMI thresholds are set correctly (60% to 120%)."""
        self.assertEqual(MaHomeBridge.min_ami_percent, 0.60)
        self.assertEqual(MaHomeBridge.max_ami_percent, 1.20)

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

    def _mock_ami_values(self, mock_hud_client, ami_60=60000, ami_100=100000):
        """Helper to mock HUD client returning different values for 60% and 100% AMI."""

        def side_effect(screen, percent, year, county_override=None):
            if percent == "60%":
                return ami_60
            elif percent == "100%":
                return ami_100
            return 0

        mock_hud_client.get_screen_mtsp_ami.side_effect = side_effect

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_cambridge_resident_passes_location_check(self, mock_hud_client):
        """Test that Cambridge residents pass the location eligibility check."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator("Cambridge", income=70000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        # Should be eligible (location passes, income in range)
        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_non_cambridge_resident_fails_location_check(self, mock_hud_client):
        """Test that non-Cambridge residents fail the location eligibility check."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator("Boston", income=70000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        # Should be ineligible (location fails)
        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_somerville_resident_fails_location_check(self, mock_hud_client):
        """Test that Somerville (adjacent to Cambridge) residents are not eligible."""
        self._mock_ami_values(mock_hud_client)

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

    def _mock_ami_values(self, mock_hud_client, ami_60=60000, ami_100=100000):
        """Helper to mock HUD client returning different values for 60% and 100% AMI."""

        def side_effect(screen, percent, year, county_override=None):
            if percent == "60%":
                return ami_60
            elif percent == "100%":
                return ami_100
            return 0

        mock_hud_client.get_screen_mtsp_ami.side_effect = side_effect

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_income_at_60_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income exactly at 60% AMI is eligible."""
        # 60% AMI = 60000, 100% AMI = 100000, so 120% AMI = 120000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=60000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_income_at_120_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income exactly at 120% AMI is eligible."""
        # 60% AMI = 60000, 100% AMI = 100000, so 120% AMI = 120000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=120000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_income_between_60_and_120_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income between 60% and 120% AMI is eligible."""
        # 60% AMI = 60000, 100% AMI = 100000, midpoint ~90% = 90000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=90000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_income_below_60_percent_ami_is_ineligible(self, mock_hud_client):
        """Test that income below 60% AMI is not eligible."""
        # 60% AMI = 60000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=50000)  # Below 60% AMI
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_income_above_120_percent_ami_is_ineligible(self, mock_hud_client):
        """Test that income above 120% AMI is not eligible."""
        # 100% AMI = 100000, so 120% AMI = 120000
        self._mock_ami_values(mock_hud_client)

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

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_hud_api_error_results_in_ineligibility(self, mock_hud_client):
        """Test that HUD API errors result in ineligibility (income cannot be verified)."""
        from integrations.clients.hud_income_limits import HudIncomeClientError

        mock_hud_client.get_screen_mtsp_ami.side_effect = HudIncomeClientError("API Error")

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

    def _mock_ami_values(self, mock_hud_client, ami_60=60000, ami_100=100000):
        """Helper to mock HUD client returning different values for 60% and 100% AMI."""

        def side_effect(screen, percent, year, county_override=None):
            if percent == "60%":
                return ami_60
            elif percent == "100%":
                return ami_100
            return 0

        mock_hud_client.get_screen_mtsp_ami.side_effect = side_effect

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_user_without_benefit_is_eligible(self, mock_hud_client):
        """Test that users who don't have the benefit can be eligible."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(has_benefit=False, income=70000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.homebridge.calculator.hud_client")
    def test_user_with_benefit_is_ineligible(self, mock_hud_client):
        """Test that users who already have the benefit are ineligible."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(has_benefit=True, income=70000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaHomeBridgeValue(TestCase):
    """Tests for benefit value calculation."""

    def test_amount_is_one(self):
        """Test that amount is 1 (FE displays 'Varies' for low_confidence programs)."""
        self.assertEqual(MaHomeBridge.amount, 1)
