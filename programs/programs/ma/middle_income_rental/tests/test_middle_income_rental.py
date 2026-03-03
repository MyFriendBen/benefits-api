"""
Unit tests for MaMiddleIncomeRental calculator class.

These tests verify the Middle-Income Rental calculator logic for Cambridge's
income-restricted rental program, including:
- Calculator registration
- Cambridge residency eligibility
- Minimum head-of-household age (18)
- Income eligibility (80%-120% AMI, with Section 8 voucher floor exemption)
- Tiered asset limit ($75,000 standard; $150,000 for all-senior or all-disabled)
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

    def test_asset_limit_is_75000(self):
        """Test that the standard asset limit is $75,000."""
        self.assertEqual(MaMiddleIncomeRental.asset_limit, 75_000)

    def test_senior_asset_limit_is_150000(self):
        """Test that the senior/disabled asset limit is $150,000."""
        self.assertEqual(MaMiddleIncomeRental.senior_asset_limit, 150_000)

    def test_min_head_age_is_18(self):
        """Test that the minimum head-of-household age is 18."""
        self.assertEqual(MaMiddleIncomeRental.min_head_age, 18)

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
        mock_screen.has_section_8 = False
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)
        mock_head = Mock()
        mock_head.age = 30
        mock_screen.get_head = Mock(return_value=mock_head)
        mock_member = Mock()
        mock_member.age = 30
        mock_member.has_disability = Mock(return_value=False)
        mock_screen.household_members = Mock()
        mock_screen.household_members.all = Mock(return_value=[mock_member])

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def _mock_ami_values(self, mock_hud_client, ami_80=80000):
        """Helper to mock HUD client returning 80% AMI."""
        mock_hud_client.get_screen_il_ami.return_value = ami_80

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


class TestMaMiddleIncomeRentalHoHAge(TestCase):
    """Tests for minimum head-of-household age requirement (18)."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, head_age, income=90000, assets=50000):
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 1
        mock_screen.household_assets = assets
        mock_screen.has_section_8 = False
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=False)
        mock_head = Mock()
        mock_head.age = head_age
        mock_screen.get_head = Mock(return_value=mock_head)
        mock_member = Mock()
        mock_member.age = head_age
        mock_member.has_disability = Mock(return_value=False)
        mock_screen.household_members = Mock()
        mock_screen.household_members.all = Mock(return_value=[mock_member])

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_hoh_age_none_is_ineligible(self, mock_hud_client):
        """Test that a head of household with unknown age is not eligible."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(head_age=None)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_hoh_age_17_is_ineligible(self, mock_hud_client):
        """Test that a head of household aged 17 is not eligible."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(head_age=17)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_hoh_age_18_is_eligible(self, mock_hud_client):
        """Test that a head of household aged 18 meets the minimum age requirement."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(head_age=18)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)


class TestMaMiddleIncomeRentalIncomeEligibility(TestCase):
    """Tests for AMI-based income eligibility check (80%-120% AMI)."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, income, household_size=4, assets=50000, has_benefit=False, has_section_8=False):
        """Helper to create a calculator with specified income."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = household_size
        mock_screen.household_assets = assets
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(side_effect=lambda name: has_section_8 if name == "section_8" else has_benefit)
        mock_head = Mock()
        mock_head.age = 35
        mock_screen.get_head = Mock(return_value=mock_head)
        mock_member = Mock()
        mock_member.age = 35
        mock_member.has_disability = Mock(return_value=False)
        mock_screen.household_members = Mock()
        mock_screen.household_members.all = Mock(return_value=[mock_member])

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def _mock_ami_80_only(self, mock_hud_client, ami_80=80_000):
        """Mock HUD client and assert the calculator always requests the 80% AMI tier."""

        def _side_effect(_screen, percent, _year, county_override=None):
            self.assertEqual(percent, "80%", f"Expected '80%' AMI request but got '{percent}'")
            return ami_80

        mock_hud_client.get_screen_il_ami.side_effect = _side_effect

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_at_80_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income exactly at 80% AMI is eligible."""
        # 80% AMI = 80000, so 120% AMI = 80000 * 1.5 = 120000
        self._mock_ami_80_only(mock_hud_client)

        calculator = self._create_calculator(income=80000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_at_120_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income exactly at 120% AMI is eligible."""
        # 80% AMI = 80000, so 120% AMI = 80000 * 1.5 = 120000
        self._mock_ami_80_only(mock_hud_client)

        calculator = self._create_calculator(income=120000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_between_80_and_120_percent_ami_is_eligible(self, mock_hud_client):
        """Test that income between 80% and 120% AMI is eligible."""
        self._mock_ami_80_only(mock_hud_client)

        calculator = self._create_calculator(income=100000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_below_80_percent_ami_is_ineligible(self, mock_hud_client):
        """Test that income below 80% AMI is not eligible."""
        self._mock_ami_80_only(mock_hud_client)

        calculator = self._create_calculator(income=70000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_income_above_120_percent_ami_is_ineligible(self, mock_hud_client):
        """Test that income above 120% AMI is not eligible."""
        # 80% AMI = 80000, so 120% AMI = 120000; income of 130000 exceeds ceiling
        self._mock_ami_80_only(mock_hud_client)

        calculator = self._create_calculator(income=130000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalSection8Voucher(TestCase):
    """Tests for Section 8 voucher floor exemption.

    Voucher holders are exempt from the 80% income floor but still subject
    to the 120% income ceiling.
    """

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, income, has_section_8, assets=50000):
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 1
        mock_screen.household_assets = assets
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(side_effect=lambda name: has_section_8 if name == "section_8" else False)
        mock_head = Mock()
        mock_head.age = 35
        mock_screen.get_head = Mock(return_value=mock_head)
        mock_member = Mock()
        mock_member.age = 35
        mock_member.has_disability = Mock(return_value=False)
        mock_screen.household_members = Mock()
        mock_screen.household_members.all = Mock(return_value=[mock_member])

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def _mock_ami_80_only(self, mock_hud_client, ami_80=80_000):
        """Mock HUD client and assert the calculator always requests the 80% AMI tier."""

        def _side_effect(_screen, percent, _year, county_override=None):
            self.assertEqual(percent, "80%", f"Expected '80%' AMI request but got '{percent}'")
            return ami_80

        mock_hud_client.get_screen_il_ami.side_effect = _side_effect

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_voucher_holder_below_80_pct_floor_is_eligible(self, mock_hud_client):
        """Voucher holders skip the 80% floor and are eligible even with low income."""
        # 80% AMI = 80000; income of 50000 is below floor but voucher exempts from it
        self._mock_ami_80_only(mock_hud_client)

        calculator = self._create_calculator(income=50000, has_section_8=True)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_voucher_holder_above_120_pct_ceiling_is_ineligible(self, mock_hud_client):
        """Voucher holders are still subject to the 120% income ceiling."""
        # 80% AMI = 80000, so 120% AMI = 120000; income of 130000 exceeds ceiling
        self._mock_ami_80_only(mock_hud_client)

        calculator = self._create_calculator(income=130000, has_section_8=True)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_non_voucher_holder_below_80_pct_floor_is_ineligible(self, mock_hud_client):
        """Non-voucher holders must meet the 80% income floor."""
        self._mock_ami_80_only(mock_hud_client)

        calculator = self._create_calculator(income=50000, has_section_8=False)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalAssetEligibility(TestCase):
    """Tests for liquid asset limit eligibility ($75,000 standard; $150,000 senior/disabled)."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, assets, income=90000, has_benefit=False, member_ages=None, all_disabled=False):
        """Helper to create a calculator with specified household assets."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = len(member_ages) if member_ages else 2
        mock_screen.household_assets = assets
        mock_screen.has_section_8 = False
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)
        mock_head = Mock()
        mock_head.age = member_ages[0] if member_ages else 35
        mock_screen.get_head = Mock(return_value=mock_head)

        members = []
        for age in member_ages or [35, 33]:
            m = Mock()
            m.age = age
            m.has_disability = Mock(return_value=all_disabled)
            members.append(m)
        mock_screen.household_members = Mock()
        mock_screen.household_members.all = Mock(return_value=members)

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_assets_at_standard_limit_are_eligible(self, mock_hud_client):
        """Test that assets exactly at $75,000 are eligible."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(assets=75_000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_assets_below_standard_limit_are_eligible(self, mock_hud_client):
        """Test that assets below $75,000 are eligible."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(assets=50_000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_assets_above_standard_limit_are_ineligible(self, mock_hud_client):
        """Test that assets above $75,000 are ineligible for standard households."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(assets=76_000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalSeniorAssetException(TestCase):
    """Tests for the $150,000 asset exception for all-senior or all-disabled households."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, assets, member_ages, all_disabled=False, income=90000):
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = len(member_ages)
        mock_screen.household_assets = assets
        mock_screen.has_section_8 = False
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=False)
        mock_head = Mock()
        mock_head.age = member_ages[0]
        mock_screen.get_head = Mock(return_value=mock_head)

        members = []
        for age in member_ages:
            m = Mock()
            m.age = age
            m.has_disability = Mock(return_value=all_disabled)
            members.append(m)
        mock_screen.household_members = Mock()
        mock_screen.household_members.all = Mock(return_value=members)

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_all_senior_household_gets_150k_limit(self, mock_hud_client):
        """All-senior (62+) household is eligible with assets up to $150,000."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(assets=100_000, member_ages=[65, 63])
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_all_disabled_household_gets_150k_limit(self, mock_hud_client):
        """All-disabled household is eligible with assets up to $150,000."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(assets=100_000, member_ages=[40, 38], all_disabled=True)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_mixed_age_household_uses_standard_75k_limit(self, mock_hud_client):
        """Mixed-age household (not all senior) uses the $75,000 standard limit."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        # One member is 65, one is 40 — not all senior
        calculator = self._create_calculator(assets=100_000, member_ages=[65, 40])
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_all_senior_household_above_150k_is_ineligible(self, mock_hud_client):
        """All-senior household with assets above $150,000 is still ineligible."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(assets=151_000, member_ages=[65, 63])
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
        mock_screen.has_section_8 = False
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)
        mock_head = Mock()
        mock_head.age = 35
        mock_screen.get_head = Mock(return_value=mock_head)
        mock_member = Mock()
        mock_member.age = 35
        mock_member.has_disability = Mock(return_value=False)
        mock_screen.household_members = Mock()
        mock_screen.household_members.all = Mock(return_value=[mock_member])

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_hud_api_error_results_in_ineligibility(self, mock_hud_client):
        """Test that HUD API errors result in ineligibility (income cannot be verified)."""
        from integrations.clients.hud_income_limits import HudIncomeClientError

        mock_hud_client.get_screen_il_ami.side_effect = HudIncomeClientError("API Error")

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
        mock_screen.has_section_8 = False
        mock_screen.white_label = Mock()
        mock_screen.white_label.state_code = "MA"
        mock_screen.calc_gross_income = Mock(return_value=income)
        mock_screen.has_benefit = Mock(return_value=has_benefit)
        mock_head = Mock()
        mock_head.age = 35
        mock_screen.get_head = Mock(return_value=mock_head)
        mock_member = Mock()
        mock_member.age = 35
        mock_member.has_disability = Mock(return_value=False)
        mock_screen.household_members = Mock()
        mock_screen.household_members.all = Mock(return_value=[mock_member])

        return MaMiddleIncomeRental(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_user_without_benefit_is_eligible(self, mock_hud_client):
        """Test that users who don't have the benefit can be eligible."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(has_benefit=False, income=90000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.middle_income_rental.calculator.hud_client")
    def test_user_with_benefit_is_ineligible(self, mock_hud_client):
        """Test that users who already have the benefit are ineligible."""
        mock_hud_client.get_screen_il_ami.return_value = 80000

        calculator = self._create_calculator(has_benefit=True, income=90000)
        eligibility = Eligibility()

        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaMiddleIncomeRentalValue(TestCase):
    """Tests for benefit value calculation."""

    def test_amount_is_one(self):
        """Test that amount is 1 (FE displays 'Varies' for this program)."""
        self.assertEqual(MaMiddleIncomeRental.amount, 1)
