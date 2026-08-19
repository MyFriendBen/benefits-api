"""
Unit tests for IL SPM-level PolicyEngine calculator classes.

These tests verify IL-specific calculator logic for SPM-level programs including:
- IlSnap calculator
- IlNslp (National School Lunch Program) calculator
- IlTanf calculator
- IlLiheap calculator
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.framework.pe_base import PolicyEngineSpmCalulator
from programs.framework.pe_dependencies import spm as spm_dependency
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from programs.programs.il.pe.spm import IlLiheap
from programs.programs.cross_white_label.nslp.base import SchoolLunch
from programs.programs.cross_white_label.nslp.il import IlNslp
from programs.programs.cross_white_label.snap.base import Snap
from programs.programs.cross_white_label.snap.il import IlSnap
from programs.programs.cross_white_label.tanf.base import Tanf
from programs.programs.cross_white_label.tanf.il import IlTanf


class TestIlSnap(TestCase):
    """Tests for Illinois SNAP calculator."""

    def test_exists_and_is_subclass_of_snap(self):
        """Test that IlSnap is a subclass of federal Snap."""
        self.assertTrue(issubclass(IlSnap, Snap))

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlSnap.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """Test that all parent Snap inputs are included."""
        for parent_input in Snap.pe_inputs:
            self.assertIn(parent_input, IlSnap.pe_inputs)


class TestIlNslp(TestCase):
    """Tests for Illinois National School Lunch Program calculator."""

    def test_exists_and_is_subclass_of_school_lunch(self):
        """Test that IlNslp is a subclass of federal SchoolLunch."""
        self.assertTrue(issubclass(IlNslp, SchoolLunch))

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlNslp.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """Test that all parent SchoolLunch inputs are included."""
        for parent_input in SchoolLunch.pe_inputs:
            self.assertIn(parent_input, IlNslp.pe_inputs)

    def test_uses_pe_net_subsidy_value(self):
        """IlNslp inherits the federal SchoolLunch value (PolicyEngine's
        school_meal_net_subsidy) rather than the removed hardcoded tier amounts."""
        self.assertEqual(IlNslp.pe_name, "school_meal_net_subsidy")
        self.assertFalse(hasattr(IlNslp, "tier_1_amount"))
        self.assertFalse(hasattr(IlNslp, "tier_2_amount"))


class TestIlTanf(TestCase):
    """Tests for Illinois TANF calculator."""

    def test_exists_and_is_subclass_of_tanf(self):
        """Test that IlTanf is a subclass of federal Tanf."""
        self.assertTrue(issubclass(IlTanf, Tanf))

    def test_pe_name_is_il_tanf(self):
        """Test that pe_name is il_tanf."""
        self.assertEqual(IlTanf.pe_name, "il_tanf")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlTanf.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """Test that all parent Tanf inputs are included."""
        for parent_input in Tanf.pe_inputs:
            self.assertIn(parent_input, IlTanf.pe_inputs)

    def test_pe_inputs_includes_il_tanf_income_dependencies(self):
        """Test that IL-specific TANF income dependencies are included."""
        self.assertIn(spm_dependency.IlTanfCountableEarnedIncomeDependency, IlTanf.pe_inputs)
        self.assertIn(spm_dependency.IlTanfCountableGrossUnearnedIncomeDependency, IlTanf.pe_inputs)

    def test_pe_outputs_includes_il_tanf(self):
        """Test that IlTanf output is in pe_outputs."""
        self.assertIn(spm_dependency.IlTanf, IlTanf.pe_outputs)


class TestIlLiheap(TestCase):
    """Tests for Illinois LIHEAP calculator."""

    def test_exists_and_is_subclass_of_policy_engine_spm_calculator(self):
        """Test that IlLiheap is a subclass of PolicyEngineSpmCalulator."""
        self.assertTrue(issubclass(IlLiheap, PolicyEngineSpmCalulator))

    def test_pe_name_is_il_liheap(self):
        """Test that pe_name is il_liheap."""
        self.assertEqual(IlLiheap.pe_name, "il_liheap")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlLiheap.pe_inputs)

    def test_pe_inputs_includes_heating_and_electricity_dependencies(self):
        """Test that energy expense dependencies are in pe_inputs."""
        self.assertIn(spm_dependency.HasHeatingCoolingExpenseDependency, IlLiheap.pe_inputs)
        self.assertIn(spm_dependency.ElectricityExpenseDependency, IlLiheap.pe_inputs)

    def test_pe_inputs_includes_heating_expense_person_dependency(self):
        """Test that HeatingExpensePersonDependency is in pe_inputs."""
        from programs.framework.pe_dependencies import member as member_dependency

        self.assertIn(member_dependency.HeatingExpensePersonDependency, IlLiheap.pe_inputs)

    def test_pe_outputs_includes_il_liheap(self):
        """Test that IlLiheap output dependency is in pe_outputs."""
        self.assertIn(spm_dependency.IlLiheap, IlLiheap.pe_outputs)

    def test_household_value_returns_zero_when_pe_returns_zero(self):
        """Test that household_value returns 0 when PE returns 0 (ineligible)."""
        mock_screen = Mock()

        calculator = IlLiheap(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_variable = Mock(return_value=0)

        result = calculator.household_value()

        self.assertEqual(result, 0)

    def test_household_value_returns_pe_benefit_amount(self):
        """Test that household_value returns the dollar amount from PE."""
        mock_screen = Mock()

        calculator = IlLiheap(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_variable = Mock(return_value=400)

        result = calculator.household_value()

        self.assertEqual(result, 400)
