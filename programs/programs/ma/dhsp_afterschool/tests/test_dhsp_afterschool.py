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
    """Tests for benefit value calculation via the value() method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_mock_member(self, age, member_id=None):
        """Helper to create a mock household member."""
        mock_member = Mock()
        mock_member.age = age
        mock_member.id = member_id if member_id is not None else age  # Use age as id if not specified
        return mock_member

    def _create_calculator(self, children_ages, county="Cambridge", has_benefit=False):
        """Helper to create a calculator with mocked screen."""
        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.household_size = 1 + len(children_ages)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        # Create mock household members (parent + children)
        members = [self._create_mock_member(35, member_id=0)]  # Parent
        for idx, age in enumerate(children_ages, start=1):
            members.append(self._create_mock_member(age, member_id=idx))
        mock_screen.household_members.all.return_value = members

        return MaDhspAfterschool(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_value_sets_household_value_for_one_eligible_child(self):
        """Test that value() sets household_value to expected annual amount for one eligible child."""
        calculator = self._create_calculator([8])  # One 8-year-old child
        eligibility = calculator.eligible()

        # Call value() to populate value fields
        calculator.value(eligibility)

        expected_annual = 900 * 12  # $10,800
        self.assertEqual(eligibility.household_value, expected_annual)

    def test_value_returns_eligibility_with_eligible_status(self):
        """Test that value() calculation returns eligibility indicating the household is eligible."""
        calculator = self._create_calculator([10])  # One eligible child
        eligibility = calculator.eligible()

        # Verify eligibility is True before value calculation
        self.assertTrue(eligibility.eligible)

        # Call value() - should not change eligibility status
        calculator.value(eligibility)

        self.assertTrue(eligibility.eligible)

    def test_value_assigns_zero_per_member_value_by_default(self):
        """Test that per-member value is 0 by default (uses base class member_amount)."""
        calculator = self._create_calculator([6, 10])  # Two eligible children
        eligibility = calculator.eligible()

        calculator.value(eligibility)

        # Find eligible children members (not the parent)
        eligible_children = [m for m in eligibility.eligible_members if m.eligible and m.member.age != 35]

        # Default member_amount is 0, so each eligible child should have value 0
        for member_eligibility in eligible_children:
            self.assertEqual(member_eligibility.value, 0)

    def test_value_does_not_set_values_when_ineligible(self):
        """Test that value() does not set values when household is ineligible."""
        calculator = self._create_calculator([8], county="Boston")  # Non-Cambridge resident
        eligibility = calculator.eligible()

        # Should be ineligible
        self.assertFalse(eligibility.eligible)

        calculator.value(eligibility)

        # household_value should remain 0 when ineligible
        self.assertEqual(eligibility.household_value, 0)


class TestMaDhspAfterschoolValueMultipleChildren(TestCase):
    """Tests for household value scaling with multiple eligible children."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _create_mock_member(self, age, member_id=None):
        """Helper to create a mock household member."""
        mock_member = Mock()
        mock_member.age = age
        mock_member.id = member_id if member_id is not None else age
        return mock_member

    def _create_calculator(self, children_ages, county="Cambridge", has_benefit=False):
        """Helper to create a calculator with mocked screen."""
        mock_screen = Mock()
        mock_screen.county = county
        mock_screen.household_size = 1 + len(children_ages)
        mock_screen.has_benefit = Mock(return_value=has_benefit)

        # Create mock household members (parent + children)
        members = [self._create_mock_member(35, member_id=0)]  # Parent
        for idx, age in enumerate(children_ages, start=1):
            members.append(self._create_mock_member(age, member_id=idx))
        mock_screen.household_members.all.return_value = members

        return MaDhspAfterschool(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_household_value_same_for_multiple_eligible_children(self):
        """Test that household_value is the same regardless of number of eligible children.

        The base class household_value() returns self.amount, which is a fixed annual value.
        This tests the current behavior - household_value does not scale with child count.
        """
        expected_annual = 900 * 12  # $10,800

        # Test with 1 eligible child
        calc_1_child = self._create_calculator([8])
        elig_1_child = calc_1_child.eligible()
        calc_1_child.value(elig_1_child)

        # Test with 3 eligible children
        calc_3_children = self._create_calculator([5, 10, 14])
        elig_3_children = calc_3_children.eligible()
        calc_3_children.value(elig_3_children)

        # household_value is fixed at self.amount, not multiplied by child count
        self.assertEqual(elig_1_child.household_value, expected_annual)
        self.assertEqual(elig_3_children.household_value, expected_annual)

    def test_total_value_equals_household_value_with_default_member_amount(self):
        """Test that total value equals household_value when member_amount is 0."""
        calculator = self._create_calculator([6, 9, 12])  # Three eligible children
        eligibility = calculator.eligible()
        calculator.value(eligibility)

        expected_annual = 900 * 12

        # Total value should equal household_value since member values are 0
        self.assertEqual(eligibility.value, expected_annual)
        self.assertEqual(eligibility.household_value, expected_annual)

    def test_eligible_members_tracked_correctly_for_multiple_children(self):
        """Test that all eligible children are tracked in eligible_members."""
        calculator = self._create_calculator([5, 10, 14])  # 3 eligible children (ages 5, 10, 14)
        eligibility = calculator.eligible()
        calculator.value(eligibility)

        # Should have 4 member eligibilities: 1 parent + 3 children
        self.assertEqual(len(eligibility.eligible_members), 4)

        # Count eligible members (children in K-8 range)
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 3)  # All 3 children are eligible

    def test_mixed_ages_only_k8_children_eligible(self):
        """Test that only K-8 age children (5-14) are marked as eligible members."""
        # Mix of ages: 3 (too young), 8 (eligible), 16 (too old)
        calculator = self._create_calculator([3, 8, 16])
        eligibility = calculator.eligible()
        calculator.value(eligibility)

        # Check member eligibility statuses
        # Index 0 is parent (age 35) - not eligible
        # Index 1 is age 3 - not eligible
        # Index 2 is age 8 - eligible
        # Index 3 is age 16 - not eligible
        member_ages_and_eligibility = [
            (m.member.age, m.eligible) for m in eligibility.eligible_members
        ]

        self.assertIn((35, False), member_ages_and_eligibility)  # Parent
        self.assertIn((3, False), member_ages_and_eligibility)   # Too young
        self.assertIn((8, True), member_ages_and_eligibility)    # Eligible
        self.assertIn((16, False), member_ages_and_eligibility)  # Too old
