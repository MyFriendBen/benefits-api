"""
Unit tests for MaDoorToDoor calculator class.

These tests verify the Door2Door Transportation calculator logic for Cambridge's
on-demand transportation program for seniors and people with mobility impairments.

Eligibility requirements:
- Cambridge residency
- Age 60+ OR has a mobility impairment (disabled, visually impaired, or long-term disability)
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ma import ma_calculators
from programs.programs.ma.door2door.calculator import MaDoorToDoor
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


class TestMaDoorToDoorCalculator(TestCase):
    """Tests for MaDoorToDoor calculator class."""

    def test_exists_and_is_subclass_of_program_calculator(self):
        """Test that MaDoorToDoor calculator class exists and inherits correctly."""
        self.assertTrue(issubclass(MaDoorToDoor, ProgramCalculator))

    def test_is_registered_in_ma_calculators(self):
        """Test that Door2Door is registered in the MA calculators dictionary."""
        self.assertIn("ma_door_to_door", ma_calculators)
        self.assertEqual(ma_calculators["ma_door_to_door"], MaDoorToDoor)

    def test_eligible_city_is_cambridge(self):
        """Test that the eligible city is set to Cambridge."""
        self.assertEqual(MaDoorToDoor.eligible_city, "Cambridge")

    def test_min_age_is_60(self):
        """Test that the minimum age is 60."""
        self.assertEqual(MaDoorToDoor.min_age, 60)

    def test_amount_is_one(self):
        """Test that amount is 1 (FE displays 'Varies')."""
        self.assertEqual(MaDoorToDoor.amount, 1)

    def test_dependencies_are_defined(self):
        """Test that required dependencies are properly defined."""
        expected_deps = ["zipcode", "age"]
        self.assertEqual(list(MaDoorToDoor.dependencies), expected_deps)


class TestMaDoorToDoorLocationEligibility(TestCase):
    """Tests for Cambridge location eligibility check."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, county, age=65, disabled=False, visually_impaired=False,
                           long_term_disability=False, has_benefit=False):
        """Helper to create a calculator with mocked screen. Returns (calculator, member_eligibility)."""
        mock_member = Mock()
        mock_member.age = age
        mock_member.disabled = disabled
        mock_member.visually_impaired = visually_impaired
        mock_member.long_term_disability = long_term_disability
        mock_member.has_disability = Mock(return_value=disabled or visually_impaired or long_term_disability)

        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.get_head = Mock(return_value=mock_member)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        calculator = MaDoorToDoor(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)
        member_eligibility = MemberEligibility(mock_member)
        return calculator, member_eligibility

    def test_cambridge_resident_age_60_passes(self):
        """Test that Cambridge residents age 60+ pass eligibility."""
        calculator, member_eligibility = self._create_calculator("Cambridge", age=65)

        household_eligibility = Eligibility()
        calculator.household_eligible(household_eligibility)
        self.assertTrue(household_eligibility.eligible)

        calculator.member_eligible(member_eligibility)
        self.assertTrue(member_eligibility.eligible)

    def test_non_cambridge_resident_fails_location_check(self):
        """Test that non-Cambridge residents fail the location eligibility check."""
        calculator, _ = self._create_calculator("Boston", age=65)

        eligibility = Eligibility()
        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)

    def test_somerville_resident_fails_location_check(self):
        """Test that Somerville (adjacent to Cambridge) residents are not eligible."""
        calculator, _ = self._create_calculator("Somerville", age=70)

        eligibility = Eligibility()
        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)


class TestMaDoorToDoorAgeEligibility(TestCase):
    """Tests for age eligibility check (60+)."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, age, disabled=False, visually_impaired=False,
                           long_term_disability=False, has_benefit=False):
        """Helper to create a calculator with specified age. Returns (calculator, member_eligibility)."""
        mock_member = Mock()
        mock_member.age = age
        mock_member.disabled = disabled
        mock_member.visually_impaired = visually_impaired
        mock_member.long_term_disability = long_term_disability
        mock_member.has_disability = Mock(return_value=disabled or visually_impaired or long_term_disability)

        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.get_head = Mock(return_value=mock_member)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        calculator = MaDoorToDoor(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)
        member_eligibility = MemberEligibility(mock_member)
        return calculator, member_eligibility

    def test_age_exactly_60_is_eligible(self):
        """Test that age exactly 60 is eligible."""
        calculator, member_eligibility = self._create_calculator(age=60)

        calculator.member_eligible(member_eligibility)

        self.assertTrue(member_eligibility.eligible)

    def test_age_over_60_is_eligible(self):
        """Test that age over 60 is eligible."""
        calculator, member_eligibility = self._create_calculator(age=75)

        calculator.member_eligible(member_eligibility)

        self.assertTrue(member_eligibility.eligible)

    def test_age_59_without_disability_is_ineligible(self):
        """Test that age 59 without disability is ineligible."""
        calculator, member_eligibility = self._create_calculator(age=59)

        calculator.member_eligible(member_eligibility)

        self.assertFalse(member_eligibility.eligible)

    def test_age_under_60_without_disability_is_ineligible(self):
        """Test that age under 60 without disability is ineligible."""
        calculator, member_eligibility = self._create_calculator(age=45)

        calculator.member_eligible(member_eligibility)

        self.assertFalse(member_eligibility.eligible)


class TestMaDoorToDoorDisabilityEligibility(TestCase):
    """Tests for mobility impairment eligibility (alternative to age 60+)."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, age, disabled=False, visually_impaired=False,
                           long_term_disability=False, has_benefit=False):
        """Helper to create a calculator with disability status. Returns (calculator, member_eligibility)."""
        mock_member = Mock()
        mock_member.age = age
        mock_member.disabled = disabled
        mock_member.visually_impaired = visually_impaired
        mock_member.long_term_disability = long_term_disability
        mock_member.has_disability = Mock(return_value=disabled or visually_impaired or long_term_disability)

        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.get_head = Mock(return_value=mock_member)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        calculator = MaDoorToDoor(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)
        member_eligibility = MemberEligibility(mock_member)
        return calculator, member_eligibility

    def test_disabled_under_60_is_eligible(self):
        """Test that disabled person under 60 is eligible."""
        calculator, member_eligibility = self._create_calculator(age=45, disabled=True)

        calculator.member_eligible(member_eligibility)

        self.assertTrue(member_eligibility.eligible)

    def test_visually_impaired_under_60_is_eligible(self):
        """Test that visually impaired person under 60 is eligible."""
        calculator, member_eligibility = self._create_calculator(age=50, visually_impaired=True)

        calculator.member_eligible(member_eligibility)

        self.assertTrue(member_eligibility.eligible)

    def test_long_term_disability_under_60_is_eligible(self):
        """Test that person with long-term disability under 60 is eligible."""
        calculator, member_eligibility = self._create_calculator(age=35, long_term_disability=True)

        calculator.member_eligible(member_eligibility)

        self.assertTrue(member_eligibility.eligible)

    def test_disabled_and_senior_is_eligible(self):
        """Test that disabled senior is eligible (both criteria met)."""
        calculator, member_eligibility = self._create_calculator(age=65, disabled=True)

        calculator.member_eligible(member_eligibility)

        self.assertTrue(member_eligibility.eligible)


class TestMaDoorToDoorHasBenefit(TestCase):
    """Tests for has_benefit behavior - users who already have the benefit should be ineligible."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_calculator(self, has_benefit=False, age=65):
        """Helper to create a calculator."""
        mock_member = Mock()
        mock_member.age = age
        mock_member.disabled = False
        mock_member.visually_impaired = False
        mock_member.long_term_disability = False
        mock_member.has_disability = Mock(return_value=False)

        mock_screen = Mock()
        mock_screen.county = "Cambridge"
        mock_screen.get_head = Mock(return_value=mock_member)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        return MaDoorToDoor(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_user_without_benefit_is_eligible(self):
        """Test that users who don't have the benefit can be eligible."""
        calculator = self._create_calculator(has_benefit=False, age=65)

        eligibility = Eligibility()
        calculator.household_eligible(eligibility)

        self.assertTrue(eligibility.eligible)

    def test_user_with_benefit_is_ineligible(self):
        """Test that users who already have the benefit are ineligible."""
        calculator = self._create_calculator(has_benefit=True, age=65)

        eligibility = Eligibility()
        calculator.household_eligible(eligibility)

        self.assertFalse(eligibility.eligible)
