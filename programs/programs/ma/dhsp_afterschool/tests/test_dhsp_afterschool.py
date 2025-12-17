"""
Unit tests for MaDhspAfterschool calculator class.

These tests verify the DHSP Afterschool Programs Lottery calculator logic
for Cambridge's K-8 afterschool program, including:
- Calculator registration
- Cambridge residency eligibility
- Child age eligibility (K-8, ages 5-14)
- Dependencies configuration
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ma import ma_calculators
from programs.programs.ma.dhsp_afterschool.calculator import MaDhspAfterschool
from programs.programs.calc import ProgramCalculator, Eligibility


class TestMaDhspAfterschoolCalculator(TestCase):
    """Tests for MaDhspAfterschool calculator class."""

    def test_exists_and_is_subclass_of_program_calculator(self):
        """Test that MaDhspAfterschool calculator class exists and inherits correctly."""
        self.assertTrue(issubclass(MaDhspAfterschool, ProgramCalculator))

    def test_is_registered_in_ma_calculators(self):
        """Test that DHSP Afterschool is registered in the MA calculators dictionary."""
        self.assertIn("ma_dhsp_afterschool", ma_calculators)
        self.assertEqual(ma_calculators["ma_dhsp_afterschool"], MaDhspAfterschool)

    def test_eligible_city_is_cambridge(self):
        """Test that the eligible city is set to Cambridge."""
        self.assertEqual(MaDhspAfterschool.eligible_city, "Cambridge")

    def test_child_age_range_is_k8(self):
        """Test that the child age range is set correctly for K-8 (ages 5-14)."""
        self.assertEqual(MaDhspAfterschool.min_child_age, 5)
        self.assertEqual(MaDhspAfterschool.max_child_age, 14)

    def test_dependencies_are_defined(self):
        """Test that required dependencies are properly defined."""
        expected_deps = ["zipcode", "household_size"]
        self.assertEqual(list(MaDhspAfterschool.dependencies), expected_deps)

    def test_amount_is_annual_value(self):
        """Test that amount is set to annual value (~$900/month * 12)."""
        self.assertEqual(MaDhspAfterschool.amount, 900 * 12)


class TestMaDhspAfterschoolLocationEligibility(TestCase):
    """Tests for Cambridge location eligibility check."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_mock_member(self, age):
        """Helper to create a mock household member."""
        mock_member = Mock()
        mock_member.age = age
        return mock_member

    def _create_calculator(self, county, children_ages, has_benefit=False):
        """Helper to create a calculator with mocked screen."""
        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.household_size = 1 + len(children_ages)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        # Create mock household members (parent + children)
        members = [self._create_mock_member(35)]  # Parent
        for age in children_ages:
            members.append(self._create_mock_member(age))
        mock_screen.household_members.all.return_value = members

        return MaDhspAfterschool(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_cambridge_resident_with_k8_child_passes(self):
        """Test that Cambridge residents with K-8 children pass eligibility."""
        calculator = self._create_calculator("Cambridge", [8])
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_non_cambridge_resident_fails_location_check(self):
        """Test that non-Cambridge residents fail the location eligibility check."""
        calculator = self._create_calculator("Boston", [8])
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_somerville_resident_fails_location_check(self):
        """Test that Somerville (adjacent to Cambridge) residents are not eligible."""
        calculator = self._create_calculator("Somerville", [8])
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)


class TestMaDhspAfterschoolChildAgeEligibility(TestCase):
    """Tests for child age eligibility check (K-8, ages 5-14)."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_mock_member(self, age):
        """Helper to create a mock household member."""
        mock_member = Mock()
        mock_member.age = age
        return mock_member

    def _create_calculator(self, children_ages, has_benefit=False):
        """Helper to create a calculator with specified children ages."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 1 + len(children_ages)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        # Create mock household members (parent + children)
        members = [self._create_mock_member(35)]  # Parent
        for age in children_ages:
            members.append(self._create_mock_member(age))
        mock_screen.household_members.all.return_value = members

        return MaDhspAfterschool(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_kindergarten_age_child_is_eligible(self):
        """Test that a kindergarten-age child (age 5) is eligible."""
        calculator = self._create_calculator([5])
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eighth_grade_age_child_is_eligible(self):
        """Test that an 8th grade child (age 14) is eligible."""
        calculator = self._create_calculator([14])
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_middle_school_age_child_is_eligible(self):
        """Test that a middle school age child (age 10) is eligible."""
        calculator = self._create_calculator([10])
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_pre_k_child_is_ineligible(self):
        """Test that a pre-K child (age 4) is not eligible."""
        calculator = self._create_calculator([4])
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_high_school_child_is_ineligible(self):
        """Test that a high school child (age 15) is not eligible."""
        calculator = self._create_calculator([15])
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_household_with_no_children_is_ineligible(self):
        """Test that a household with no children is not eligible."""
        calculator = self._create_calculator([])
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)

    def test_household_with_multiple_k8_children_is_eligible(self):
        """Test that a household with multiple K-8 children is eligible."""
        calculator = self._create_calculator([6, 9, 12])
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_household_with_mixed_ages_is_eligible_if_one_k8(self):
        """Test that a household is eligible if at least one child is K-8."""
        calculator = self._create_calculator([3, 8, 17])  # Pre-K, 3rd grade, high school
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_household_with_only_ineligible_ages_is_ineligible(self):
        """Test that a household with only ineligible age children is not eligible."""
        calculator = self._create_calculator([2, 16])  # Toddler, high school
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)


class TestMaDhspAfterschoolHasBenefit(TestCase):
    """Tests for has_benefit behavior - users who already have the benefit should be ineligible."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_mock_member(self, age):
        """Helper to create a mock household member."""
        mock_member = Mock()
        mock_member.age = age
        return mock_member

    def _create_calculator(self, has_benefit=False):
        """Helper to create a calculator."""
        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.household_size = 2
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        # Create mock household members (parent + child)
        members = [self._create_mock_member(35), self._create_mock_member(8)]
        mock_screen.household_members.all.return_value = members

        return MaDhspAfterschool(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_user_without_benefit_is_eligible(self):
        """Test that users who don't have the benefit can be eligible."""
        calculator = self._create_calculator(has_benefit=False)
        eligibility = calculator.eligible()

        self.assertTrue(eligibility.eligible)

    def test_user_with_benefit_is_ineligible(self):
        """Test that users who already have the benefit are ineligible."""
        calculator = self._create_calculator(has_benefit=True)
        eligibility = calculator.eligible()

        self.assertFalse(eligibility.eligible)


class TestMaDhspAfterschoolValue(TestCase):
    """Tests for benefit value calculation."""

    def test_amount_is_annual_childcare_savings(self):
        """Test that amount represents annual childcare savings (~$900/month)."""
        expected_annual = 900 * 12  # $10,800
        self.assertEqual(MaDhspAfterschool.amount, expected_annual)
