"""
Unit tests for MaCpp calculator class.

These tests verify the Cambridge Preschool Program (CPP) calculator logic,
including:
- Calculator registration and class attributes
- Cambridge residency eligibility
- Child age eligibility (ages 3-4)
- Income eligibility for 3-year-olds (≤65% AMI, interpolated from 60%+70% MTSP)
- No income restriction for 4-year-olds
- has_benefit exclusion
- Mixed-household scenarios
"""

from django.test import TestCase
from unittest.mock import Mock, patch

from programs.programs.ma import ma_calculators
from programs.programs.ma.cpp.calculator import MaCpp
from programs.programs.calc import ProgramCalculator


class TestMaCppCalculator(TestCase):
    """Tests for MaCpp calculator class attributes and registration."""

    def test_exists_and_is_subclass_of_program_calculator(self):
        """Test that MaCpp calculator class exists and inherits correctly."""
        self.assertTrue(issubclass(MaCpp, ProgramCalculator))

    def test_is_registered_in_ma_calculators(self):
        """Test that CPP is registered in the MA calculators dictionary."""
        self.assertIn("ma_cpp", ma_calculators)
        self.assertEqual(ma_calculators["ma_cpp"], MaCpp)

    def test_eligible_city_is_cambridge(self):
        """Test that the eligible city is set to Cambridge."""
        self.assertEqual(MaCpp.eligible_city, "Cambridge")

    def test_child_age_range_is_preschool(self):
        """Test that the child age range is set correctly for preschool (ages 3-4)."""
        self.assertEqual(MaCpp.min_child_age, 3)
        self.assertEqual(MaCpp.max_child_age, 4)

    def test_hud_county_is_middlesex(self):
        """Test that the HUD county is Middlesex (Cambridge's county)."""
        self.assertEqual(MaCpp.hud_county, "Middlesex")

    def test_uses_approximate_for_65_percent_ami(self):
        """Test that 65% AMI is estimated via hud_client.approximate_screen_mtsp_ami (no class attribute)."""
        # 65% AMI is looked up at runtime via approximate_screen_mtsp_ami("65%", ...).
        # There is intentionally no max_ami_percent class attribute.
        self.assertFalse(hasattr(MaCpp, "max_ami_percent"))

    def test_dependencies_are_defined(self):
        """Test that required dependencies are properly defined."""
        expected_deps = [
            "income_amount",
            "income_frequency",
            "household_size",
            "county",
        ]
        self.assertEqual(list(MaCpp.dependencies), expected_deps)

    def test_amount_is_one_for_varies(self):
        """Test that amount is 1 (frontend displays 'Varies' for free preschool)."""
        self.assertEqual(MaCpp.amount, 1)


class TestMaCppLocationEligibility(TestCase):
    """Tests for Cambridge location eligibility check."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, county, children_ages, has_benefit=False):
        """Helper to create a calculator with mocked screen."""
        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.household_size = 1 + len(children_ages)
        mock_screen.has_benefit = Mock(return_value=has_benefit)
        mock_screen.calc_gross_income.return_value = 10000  # Low income

        members = [Mock(age=35)]  # Parent
        for age in children_ages:
            members.append(Mock(age=age))
        mock_screen.household_members.all.return_value = members

        return MaCpp(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_cambridge_resident_with_preschool_child_passes(self, mock_hud_client):
        """Test that Cambridge residents with a 3-year-old below income limit are eligible."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 80000
        calculator = self._create_calculator("Cambridge", [3])
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    def test_non_cambridge_resident_fails(self):
        """Test that non-Cambridge residents are not eligible (Scenario 7)."""
        calculator = self._create_calculator("Somerville", [4])
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    def test_boston_resident_fails(self):
        """Test that Boston residents are not eligible."""
        calculator = self._create_calculator("Boston", [4])
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)


class TestMaCppMemberEligibility(TestCase):
    """Tests for child age eligibility and income checks."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(
        self,
        children_ages,
        gross_income_yearly=10000,
        county="Cambridge",
        has_benefit=False,
    ):
        """Helper to create a calculator with mocked screen."""
        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.household_size = 1 + len(children_ages)
        mock_screen.has_benefit = Mock(return_value=has_benefit)
        mock_screen.calc_gross_income.return_value = gross_income_yearly

        members = [Mock(age=35)]  # Parent
        for age in children_ages:
            members.append(Mock(age=age))
        mock_screen.household_members.all.return_value = members

        return MaCpp(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_scenario1_three_year_old_low_income_eligible(self, mock_hud_client):
        """Scenario 1: 3-year-old Cambridge family well below income limit → Eligible."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 80000
        # $2,000/month = $24,000/year → well below 65% AMI
        calculator = self._create_calculator([3], gross_income_yearly=24000)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_scenario2_four_year_old_high_income_eligible(self, mock_hud_client):
        """Scenario 2: 4-year-old with high income → Eligible (no income restriction for 4yo)."""
        # HUD client should NOT be called for a 4-year-old
        calculator = self._create_calculator([4], gross_income_yearly=180000)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)
        mock_hud_client.approximate_screen_mtsp_ami.assert_not_called()

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_scenario3_three_year_old_just_below_income_limit_eligible(self, mock_hud_client):
        """Scenario 3: 3-year-old, income just below interpolated 65% AMI threshold → Eligible."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 75000
        calculator = self._create_calculator([3], gross_income_yearly=74999)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_scenario4_three_year_old_just_above_income_limit_ineligible(self, mock_hud_client):
        """Scenario 4: 3-year-old, income just above interpolated 65% AMI threshold → Not eligible."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 75000
        calculator = self._create_calculator([3], gross_income_yearly=75001)
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_calls_approximate_with_65_percent(self, mock_hud_client):
        """Calculator calls approximate_screen_mtsp_ami with '65%' for 3-year-old income check.

        Uses a realistic Middlesex County interpolated value:
          65% MTSP HH2 ≈ $84,120  →  close to CPP guideline of $83,655
        """
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 84120
        calculator = self._create_calculator([3], gross_income_yearly=84000)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)  # 84000 <= 84120

        # Verify approximate_screen_mtsp_ami was called with "65%"
        mock_hud_client.approximate_screen_mtsp_ami.assert_called_once()
        call_args = mock_hud_client.approximate_screen_mtsp_ami.call_args
        self.assertEqual(call_args[0][1], "65%")

    def test_scenario5_child_age_2_too_young_ineligible(self):
        """Scenario 5: Child age 2 (too young) → Not eligible."""
        calculator = self._create_calculator([2])
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    def test_scenario6_child_age_5_too_old_ineligible(self):
        """Scenario 6: Child age 5 (too old) → Not eligible."""
        calculator = self._create_calculator([5])
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    def test_scenario10_no_children_ineligible(self):
        """Scenario 10: No children in household → Not eligible."""
        calculator = self._create_calculator([])
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_scenario9_mixed_household_3yo_eligible_6yo_not(self, mock_hud_client):
        """Scenario 9: Household with 3-year-old and 6-year-old → Eligible (3yo qualifies)."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 80000
        calculator = self._create_calculator([3, 6], gross_income_yearly=24000)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_mixed_household_3yo_and_4yo_high_income_only_4yo_eligible(self, mock_hud_client):
        """Mixed household: 3yo + 4yo with income above limit → only 4yo is eligible member."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 60000
        # Income above limit for 3yo, but 4yo has no income restriction
        calculator = self._create_calculator([3, 4], gross_income_yearly=70000)
        eligibility = calculator.eligible()

        # Household is eligible because the 4-year-old qualifies
        self.assertTrue(eligibility.eligible)

        # Check per-member results: 3yo ineligible, 4yo eligible
        child_eligibilities = [m for m in eligibility.eligible_members if m.member.age in [3, 4]]
        three_yo = next(m for m in child_eligibilities if m.member.age == 3)
        four_yo = next(m for m in child_eligibilities if m.member.age == 4)
        self.assertFalse(three_yo.eligible)
        self.assertTrue(four_yo.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_hud_api_error_marks_3yo_ineligible(self, mock_hud_client):
        """HUD API error for a 3-year-old → member ineligible (conservative behavior)."""
        from integrations.clients.hud_income_limits import HudIncomeClientError

        mock_hud_client.approximate_screen_mtsp_ami.side_effect = HudIncomeClientError("API error")
        calculator = self._create_calculator([3])
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_hud_api_not_called_for_4yo(self, mock_hud_client):
        """HUD API should not be called when only 4-year-olds are present."""
        calculator = self._create_calculator([4])
        calculator.eligible()
        mock_hud_client.approximate_screen_mtsp_ami.assert_not_called()

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_income_exactly_at_limit_eligible(self, mock_hud_client):
        """3-year-old with income exactly at the limit → Eligible (≤ not <)."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 60000
        calculator = self._create_calculator([3], gross_income_yearly=60000)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)


class TestMaCppHasBenefit(TestCase):
    """Tests for has_benefit exclusion (already enrolled households)."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, has_benefit=False):
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 2
        mock_screen.has_benefit = Mock(return_value=has_benefit)
        mock_screen.calc_gross_income.return_value = 10000

        members = [Mock(age=35), Mock(age=4)]
        mock_screen.household_members.all.return_value = members

        return MaCpp(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_without_benefit_is_eligible(self):
        """Test that households without the benefit can be eligible."""
        calculator = self._create_calculator(has_benefit=False)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    def test_scenario8_already_has_benefit_ineligible(self):
        """Scenario 8: Household already enrolled in CPP → Not eligible."""
        calculator = self._create_calculator(has_benefit=True)
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)


class TestMaCppFosterCare(TestCase):
    """Tests for foster care eligibility — foster children bypass the 3yo income restriction."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, child_age: int, relationship: str, gross_income_yearly: int = 10000):
        """Helper to create a calculator with a single child of the given age and relationship."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 2
        mock_screen.has_benefit = Mock(return_value=False)
        mock_screen.calc_gross_income.return_value = gross_income_yearly

        parent = Mock(age=35, relationship="headOfHousehold")
        child = Mock(age=child_age, relationship=relationship)
        mock_screen.household_members.all.return_value = [parent, child]

        return MaCpp(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_foster_child_age_3_above_income_limit_is_eligible(self, mock_hud_client):
        """Foster care child age 3 with income above 65% AMI → Eligible (bypasses income check)."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 84120
        # $10,000/month = $120,000/year, well above the ~$84,120 interpolated 65% AMI limit
        calculator = self._create_calculator(child_age=3, relationship="fosterChild", gross_income_yearly=120000)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_foster_child_age_3_does_not_call_hud_api(self, mock_hud_client):
        """HUD API should not be called for a 3-year-old foster child."""
        calculator = self._create_calculator(child_age=3, relationship="fosterChild", gross_income_yearly=120000)
        calculator.eligible()
        mock_hud_client.approximate_screen_mtsp_ami.assert_not_called()

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_non_foster_child_age_3_above_income_limit_is_ineligible(self, mock_hud_client):
        """Non-foster child age 3 with income above 65% AMI → Not eligible (income check applies)."""
        mock_hud_client.approximate_screen_mtsp_ami.return_value = 84120
        calculator = self._create_calculator(child_age=3, relationship="child", gross_income_yearly=120000)
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    @patch("programs.programs.ma.cpp.calculator.hud_client")
    def test_foster_child_age_4_is_eligible(self, mock_hud_client):
        """Foster care child age 4 → Eligible (4-year-olds always pass regardless of relation)."""
        calculator = self._create_calculator(child_age=4, relationship="fosterChild", gross_income_yearly=120000)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)
        mock_hud_client.approximate_screen_mtsp_ami.assert_not_called()


class TestMaCppValue(TestCase):
    """Tests for benefit value calculation."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, children_ages):
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 1 + len(children_ages)
        mock_screen.has_benefit = Mock(return_value=False)
        mock_screen.calc_gross_income.return_value = 10000

        members = [Mock(age=35, id=0)]
        for idx, age in enumerate(children_ages, start=1):
            m = Mock()
            m.age = age
            m.id = idx
            members.append(m)
        mock_screen.household_members.all.return_value = members

        return MaCpp(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_value_is_one_for_eligible_household(self):
        """Test that household value is 1 (representing 'Varies')."""
        calculator = self._create_calculator([4])
        eligibility = calculator.eligible()
        calculator.value(eligibility)
        self.assertEqual(eligibility.household_value, 1)

    def test_value_is_zero_when_ineligible(self):
        """Test that value remains 0 when household is ineligible."""
        mock_screen = Mock()
        mock_screen.county = "Somerville"  # Not Cambridge
        mock_screen.household_size = 2
        mock_screen.has_benefit = Mock(return_value=False)
        members = [Mock(age=35, id=0), Mock(age=4, id=1)]
        mock_screen.household_members.all.return_value = members

        calculator = MaCpp(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)
        eligibility = calculator.eligible()
        calculator.value(eligibility)
        self.assertEqual(eligibility.household_value, 0)
