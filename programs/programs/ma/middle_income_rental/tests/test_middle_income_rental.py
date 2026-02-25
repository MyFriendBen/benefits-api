"""
Unit tests for MaMiddleIncomeRental calculator class.

These tests verify the Middle-Income Rental calculator logic for Cambridge's
income-restricted rental program, including:
- Calculator registration
- Cambridge residency eligibility
- Income eligibility (80%-120% AMI)
- Asset limit eligibility ($100,000)
- HUD API error handling
- has_benefit behavior
"""

from django.test import TestCase
from unittest.mock import Mock, patch

from programs.programs.ma import ma_calculators
from programs.programs.ma.middle_income_rental.calculator import MaMiddleIncomeRental
from programs.programs.calc import ProgramCalculator, Eligibility


class TestMaMiddleIncomeRentalCalculator(TestCase):
    """Tests for MaMiddleIncomeRental calculator class attributes and registration."""

    def test_exists_and_is_subclass_of_program_calculator(self):
        """Test that MaMiddleIncomeRental calculator class exists and inherits correctly."""
        self.assertTrue(issubclass(MaMiddleIncomeRental, ProgramCalculator))

    def test_is_registered_in_ma_calculators(self):
        """Test that Middle-Income Rental is registered in the MA calculators dictionary."""
        self.assertIn("ma_middle_income_rental", ma_calculators)
        self.assertEqual(ma_calculators["ma_middle_income_rental"], MaMiddleIncomeRental)

    def test_eligible_city_is_cambridge(self):
        """Test that the eligible city is set to Cambridge."""
        self.assertEqual(MaMiddleIncomeRental.eligible_city, "Cambridge")

    def test_hud_county_is_middlesex(self):
        """Test that the HUD county is Middlesex (Cambridge is in Middlesex County)."""
        self.assertEqual(MaMiddleIncomeRental.hud_county, "Middlesex")

    def test_ami_thresholds_are_correct(self):
        """Test that AMI thresholds are set correctly (80% to 120%)."""
        self.assertEqual(MaMiddleIncomeRental.min_ami_percent, 0.80)
        self.assertEqual(MaMiddleIncomeRental.max_ami_percent, 1.20)

    def test_asset_limit_is_100000(self):
        """Test that the asset limit is $100,000."""
        self.assertEqual(MaMiddleIncomeRental.asset_limit, 100_000)

    def test_dependencies_are_defined(self):
        """Test that required dependencies are properly defined."""
        expected_deps = ["zipcode", "income_amount", "income_frequency", "household_size", "household_assets"]
        self.assertEqual(list(MaMiddleIncomeRental.dependencies), expected_deps)


class TestMaMiddleIncomeRentalLocationEligibility(TestCase):
    """Tests for Cambridge location eligibility check."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, county, household_size=4, income=100000, assets=50000, has_benefit=False):
        """Helper to create a calculator with mocked screen."""
        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.household_size = household_size
        mock_screen.household_assets = assets
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def _mock_ami_values(self, mock_hud_client, ami_80=80000, ami_100=100000):
        """Helper to mock HUD client returning different values for 80% and 100% AMI."""

        def side_effect(_screen, percent, _year, **_kwargs):
            if percent == "80%":
                return ami_80
            elif percent == "100%":
                return ami_100
            return 0

        mock_hud_client.get_screen_mtsp_ami.side_effect = side_effect

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_cambridge_resident_passes_location_check(self, mock_hud_client):
        """Test that Cambridge residents pass the location eligibility check."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator("Cambridge", income=90000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_non_cambridge_resident_fails_location_check(self, mock_hud_client):
        """Test that non-Cambridge residents fail the location eligibility check."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator("Boston", income=90000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_somerville_resident_fails_location_check(self, mock_hud_client):
        """Test that Somerville (adjacent to Cambridge) residents are not eligible."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator("Somerville", income=90000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalIncomeEligibility(TestCase):
    """Tests for AMI-based income eligibility check (80%-120% AMI)."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, income, household_size=4, assets=50000, has_benefit=False):
        """Helper to create a calculator with specified income."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = household_size
        mock_screen.household_assets = assets
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def _mock_ami_values(self, mock_hud_client, ami_80=80000, ami_100=100000):
        """Helper to mock HUD client returning different values for 80% and 100% AMI."""

        def side_effect(_screen, percent, _year, **_kwargs):
            if percent == "80%":
                return ami_80
            elif percent == "100%":
                return ami_100
            return 0

        mock_hud_client.get_screen_mtsp_ami.side_effect = side_effect

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_at_80_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income exactly at 80% AMI is eligible."""
        # 80% AMI = 80000, 100% AMI = 100000, so 120% AMI = 120000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=80000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_at_120_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income exactly at 120% AMI is eligible."""
        # 80% AMI = 80000, 100% AMI = 100000, so 120% AMI = 120000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=120000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_between_80_and_120_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income between 80% and 120% AMI is eligible."""
        # 80% AMI = 80000, 100% AMI = 100000; midpoint ~100% = 100000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=100000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_below_80_percent_ami_is_ineligible(self, mock_hud_client):
        """Test that income below 80% AMI is not eligible."""
        # 80% AMI = 80000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=70000)  # Below 80% AMI
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_above_120_percent_ami_is_ineligible(self, mock_hud_client):
        """Test that income above 120% AMI is not eligible."""
        # 100% AMI = 100000, so 120% AMI = 120000
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(income=130000)  # Above 120% AMI
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalAssetEligibility(TestCase):
    """Tests for liquid asset limit eligibility ($100,000)."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, assets, income=90000, has_benefit=False):
        """Helper to create a calculator with specified household assets."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 2
        mock_screen.household_assets = assets
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def _mock_ami_values(self, mock_hud_client, ami_80=80000, ami_100=100000):
        """Helper to mock HUD client."""

        def side_effect(_screen, percent, _year, **_kwargs):
            if percent == "80%":
                return ami_80
            elif percent == "100%":
                return ami_100
            return 0

        mock_hud_client.get_screen_mtsp_ami.side_effect = side_effect

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_assets_at_limit_are_eligible(self, mock_hud_client):
        """Test that assets exactly at $100,000 are eligible."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(assets=100_000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_assets_below_limit_are_eligible(self, mock_hud_client):
        """Test that assets below $100,000 are eligible."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(assets=50_000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_assets_above_limit_are_ineligible(self, mock_hud_client):
        """Test that assets above $100,000 are ineligible."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(assets=101_000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalHudApiError(TestCase):
    """Tests for HUD API error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, income=90000, assets=50000, has_benefit=False):
        """Helper to create a calculator."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 4
        mock_screen.household_assets = assets
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_hud_api_error_results_in_ineligibility(self, mock_hud_client):
        """Test that HUD API errors result in ineligibility (income cannot be verified)."""
        from integrations.clients.hud_income_limits import HudIncomeClientError

        mock_hud_client.get_screen_mtsp_ami.side_effect = HudIncomeClientError("API Error")

        calculator = self._create_calculator()
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalHasBenefit(TestCase):
    """Tests for has_benefit behavior — users who already have the benefit should be ineligible."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, has_benefit=False, income=90000, assets=50000):
        """Helper to create a calculator."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 4
        mock_screen.household_assets = assets
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def _mock_ami_values(self, mock_hud_client, ami_80=80000, ami_100=100000):
        """Helper to mock HUD client."""

        def side_effect(_screen, percent, _year, **_kwargs):
            if percent == "80%":
                return ami_80
            elif percent == "100%":
                return ami_100
            return 0

        mock_hud_client.get_screen_mtsp_ami.side_effect = side_effect

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_user_without_benefit_is_eligible(self, mock_hud_client):
        """Test that users who don't have the benefit can be eligible."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(has_benefit=False, income=90000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_user_with_benefit_is_ineligible(self, mock_hud_client):
        """Test that users who already have the benefit are ineligible."""
        self._mock_ami_values(mock_hud_client)

        calculator = self._create_calculator(has_benefit=True, income=90000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalValue(TestCase):
    """Tests for benefit value calculation."""

    def test_amount_is_one(self):
        """Test that amount is 1 (FE displays 'Varies' for this program)."""
        self.assertEqual(MaMiddleIncomeRental.amount, 1)
