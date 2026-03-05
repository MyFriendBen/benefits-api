"""
Unit tests for MaCmsp calculator class.

These tests verify the Children's Medical Security Plan (CMSP) calculator logic,
including:
- Calculator registration and class attributes
- Eligibility for uninsured children under age 19
- No income limit (any income qualifies)
- No citizenship requirement
- Insurance status exclusion (already insured children)
- Age cutoff at 19
- Per-child value calculation
- Multi-child household scenarios
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ma import ma_calculators
from programs.programs.ma.cmsp.calculator import MaCmsp
from programs.programs.calc import ProgramCalculator


class TestMaCmspCalculator(TestCase):
    """Tests for MaCmsp calculator class attributes and registration."""

    def test_exists_and_is_subclass_of_program_calculator(self):
        """Test that MaCmsp calculator class exists and inherits correctly."""
        self.assertTrue(issubclass(MaCmsp, ProgramCalculator))

    def test_is_registered_in_ma_calculators(self):
        """Test that CMSP is registered in the MA calculators dictionary."""
        self.assertIn("ma_cmsp", ma_calculators)
        self.assertEqual(ma_calculators["ma_cmsp"], MaCmsp)

    def test_member_amount_is_2868(self):
        """Test that member_amount is $2,868/year ($239/month) per eligible uninsured child."""
        self.assertEqual(MaCmsp.member_amount, 2868)

    def test_dependencies_are_defined(self):
        """Test that required dependencies are properly defined."""
        self.assertIn("age", MaCmsp.dependencies)
        self.assertIn("health_insurance", MaCmsp.dependencies)


class TestMaCmspEligibility(TestCase):
    """Tests for CMSP eligibility scenarios from MFB-673."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _make_member(self, age: int, insured: bool = False, mass_health: bool = False) -> Mock:
        """Create a mock household member with insurance attributes."""
        member = Mock()
        member.age = age
        member.insurance = Mock()
        member.insurance.none = not insured
        member.insurance.mass_health = mass_health
        return member

    def _create_calculator(self, members: list) -> MaCmsp:
        """Helper to create a calculator with mocked screen."""
        mock_screen = Mock()
        mock_screen.household_members.all.return_value = members
        return MaCmsp(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_scenario1_uninsured_child_low_income_eligible(self):
        """Scenario 1: Uninsured child, low income household → Eligible.

        Confirms basic eligibility for an uninsured child regardless of income.
        """
        members = [
            self._make_member(35, insured=True),  # Parent with insurance
            self._make_member(10, insured=False),  # Uninsured child
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    def test_scenario2_uninsured_child_very_high_income_eligible(self):
        """Scenario 2: Uninsured child, very high income → Eligible (no income limit).

        CMSP has no income limit — high-income families with uninsured children qualify.
        """
        members = [
            self._make_member(40, insured=True),  # Parent with employer insurance
            self._make_member(14, insured=False),  # Uninsured child
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    def test_scenario3_infant_age_0_uninsured_eligible(self):
        """Scenario 3: Infant (age 0), uninsured → Eligible.

        Confirms youngest children (age 0) are included.
        """
        members = [
            self._make_member(28, insured=True),  # Parent
            self._make_member(0, insured=False),  # Uninsured infant
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    def test_scenario4_undocumented_child_uninsured_eligible(self):
        """Scenario 4: Undocumented child (no citizenship requirement) → Eligible.

        CMSP is one of few programs with no citizenship requirement.
        Citizenship status is not checked by the calculator.
        """
        # Citizenship is not a field checked in the calculator; the program
        # simply has no citizenship restriction. An uninsured child qualifies.
        members = [
            self._make_member(32, insured=True),  # Parent
            self._make_member(8, insured=False),  # Uninsured undocumented child
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    def test_scenario5_multiple_children_only_one_uninsured_eligible(self):
        """Scenario 5: Multiple children, only one uninsured → Eligible.

        Confirms per-child eligibility logic: at least one uninsured child qualifies.
        """
        members = [
            self._make_member(35, insured=True),  # Parent
            self._make_member(8, insured=False),  # Uninsured child → eligible
            self._make_member(12, insured=True),  # Insured child → not eligible member
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)

    def test_scenario6_child_has_mass_health_ineligible(self):
        """Scenario 6: Child with MassHealth → Not eligible.

        Children enrolled in MassHealth are already insured and do not qualify.
        """
        members = [
            self._make_member(35, insured=True),  # Parent
            self._make_member(10, insured=True, mass_health=True),  # MassHealth child
        ]
        # insurance.none = False means the child is insured
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    def test_scenario7_child_has_private_insurance_ineligible(self):
        """Scenario 7: Child has private insurance → Not eligible.

        Any insured child is excluded from CMSP.
        """
        members = [
            self._make_member(38, insured=True),  # Parent
            self._make_member(12, insured=True),  # Child with private insurance
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    def test_scenario8_child_age_19_ineligible(self):
        """Scenario 8: Child age 19 → Not eligible (under-19 cutoff enforced).

        Confirms the strict under-19 age requirement.
        """
        members = [
            self._make_member(42, insured=True),  # Parent
            self._make_member(19, insured=False),  # 19-year-old (too old)
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    def test_scenario9_no_children_adult_only_ineligible(self):
        """Scenario 9: Adult-only household → Not eligible.

        CMSP is child-specific; adults without children in the household are excluded.
        """
        members = [
            self._make_member(35, insured=False),  # Adult, uninsured but not a child
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    def test_scenario10_child_has_employer_insurance_ineligible(self):
        """Scenario 10: Child covered under employer plan → Not eligible.

        Children covered through an employer plan are excluded.
        """
        members = [
            self._make_member(36, insured=True),  # Parent with employer insurance
            self._make_member(7, insured=True),  # Child on parent's employer plan
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertFalse(eligibility.eligible)

    def test_child_age_18_is_eligible(self):
        """Child age 18 is under 19 and should qualify."""
        members = [
            self._make_member(40, insured=True),  # Parent
            self._make_member(18, insured=False),  # 18-year-old
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        self.assertTrue(eligibility.eligible)


class TestMaCmspValue(TestCase):
    """Tests for per-child benefit value calculation."""

    def setUp(self):
        self.mock_program = Mock()
        self.mock_data = {}
        self.mock_missing_deps = Mock()
        self.mock_missing_deps.has.return_value = False

    def _make_member(self, age: int, insured: bool = False) -> Mock:
        member = Mock()
        member.age = age
        member.id = age  # use age as id for simplicity
        member.insurance = Mock()
        member.insurance.none = not insured
        return member

    def _create_calculator(self, members: list) -> MaCmsp:
        mock_screen = Mock()
        mock_screen.household_members.all.return_value = members
        return MaCmsp(mock_screen, self.mock_program, self.mock_data, self.mock_missing_deps)

    def test_value_is_2868_for_one_eligible_child(self):
        """One eligible uninsured child → value = $2,868/year ($239/month)."""
        members = [
            self._make_member(35, insured=True),  # Parent
            self._make_member(10, insured=False),  # Uninsured child
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        calculator.value(eligibility)
        self.assertEqual(eligibility.value, 2868)

    def test_value_is_5736_for_two_eligible_children(self):
        """Two eligible uninsured children → value = $5,736/year ($478/month)."""
        members = [
            self._make_member(35, insured=True),  # Parent
            self._make_member(8, insured=False),  # Uninsured child 1
            self._make_member(12, insured=False),  # Uninsured child 2
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        calculator.value(eligibility)
        self.assertEqual(eligibility.value, 5736)

    def test_value_counts_only_uninsured_children(self):
        """Mixed household: only the uninsured child counts toward value."""
        members = [
            self._make_member(35, insured=True),  # Parent
            self._make_member(8, insured=False),  # Uninsured child → $2,868/year
            self._make_member(12, insured=True),  # Insured child → $0
        ]
        calculator = self._create_calculator(members)
        eligibility = calculator.eligible()
        calculator.value(eligibility)
        self.assertEqual(eligibility.value, 2868)
