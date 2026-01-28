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

from programs.programs.policyengine.calculators.base import PolicyEngineSpmCalulator
from programs.programs.policyengine.calculators.dependencies import spm as spm_dependency
from programs.programs.policyengine.calculators.dependencies import household as household_dependency
from programs.programs.policyengine.calculators.dependencies.household import IlStateCodeDependency
from programs.programs.federal.pe.spm import Snap, SchoolLunch, Tanf
from programs.programs.il.pe import il_pe_calculators, il_spm_calculators
from programs.programs.il.pe.spm import IlSnap, IlNslp, IlTanf, IlLiheap


class TestIlSnap(TestCase):
    """Tests for Illinois SNAP calculator."""

    def test_exists_and_is_subclass_of_snap(self):
        """Test that IlSnap is a subclass of federal Snap."""
        self.assertTrue(issubclass(IlSnap, Snap))

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlSnap is registered in the calculators dictionary."""
        self.assertIn("il_snap", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_snap"], IlSnap)

    def test_is_registered_in_il_spm_calculators(self):
        """Test that IlSnap is registered in the SPM calculators dictionary."""
        self.assertIn("il_snap", il_spm_calculators)
        self.assertEqual(il_spm_calculators["il_snap"], IlSnap)

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

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlNslp is registered in the calculators dictionary."""
        self.assertIn("il_nslp", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_nslp"], IlNslp)

    def test_is_registered_in_il_spm_calculators(self):
        """Test that IlNslp is registered in the SPM calculators dictionary."""
        self.assertIn("il_nslp", il_spm_calculators)
        self.assertEqual(il_spm_calculators["il_nslp"], IlNslp)

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlNslp.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """Test that all parent SchoolLunch inputs are included."""
        for parent_input in SchoolLunch.pe_inputs:
            self.assertIn(parent_input, IlNslp.pe_inputs)

    def test_tier_1_fpl_is_130_percent(self):
        """Test that tier 1 FPL threshold is 130%."""
        self.assertEqual(IlNslp.tier_1_fpl, 1.30)

    def test_tier_2_fpl_is_185_percent(self):
        """Test that tier 2 FPL threshold is 185%."""
        self.assertEqual(IlNslp.tier_2_fpl, 1.85)

    def test_tier_1_amount_is_935(self):
        """Test that tier 1 benefit amount is $935."""
        self.assertEqual(IlNslp.tier_1_amount, 935)

    def test_tier_2_amount_is_805(self):
        """Test that tier 2 benefit amount is $805."""
        self.assertEqual(IlNslp.tier_2_amount, 805)


class TestIlTanf(TestCase):
    """Tests for Illinois TANF calculator."""

    def test_exists_and_is_subclass_of_tanf(self):
        """Test that IlTanf is a subclass of federal Tanf."""
        self.assertTrue(issubclass(IlTanf, Tanf))

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlTanf is registered in the calculators dictionary."""
        self.assertIn("il_tanf", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_tanf"], IlTanf)

    def test_is_registered_in_il_spm_calculators(self):
        """Test that IlTanf is registered in the SPM calculators dictionary."""
        self.assertIn("il_tanf", il_spm_calculators)
        self.assertEqual(il_spm_calculators["il_tanf"], IlTanf)

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

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlLiheap is registered in the calculators dictionary."""
        self.assertIn("il_liheap", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_liheap"], IlLiheap)

    def test_is_registered_in_il_spm_calculators(self):
        """Test that IlLiheap is registered in the SPM calculators dictionary."""
        self.assertIn("il_liheap", il_spm_calculators)
        self.assertEqual(il_spm_calculators["il_liheap"], IlLiheap)

    def test_pe_name_is_il_liheap_income_eligible(self):
        """Test that pe_name uses income eligibility check."""
        self.assertEqual(IlLiheap.pe_name, "il_liheap_income_eligible")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlLiheap.pe_inputs)

    def test_pe_outputs_includes_il_liheap_income_eligible(self):
        """Test that IlLiheapIncomeEligible output is in pe_outputs."""
        self.assertIn(spm_dependency.IlLiheapIncomeEligible, IlLiheap.pe_outputs)

    def test_benefit_amounts_defined_for_household_sizes(self):
        """Test that benefit amounts are defined for household sizes 1-6."""
        self.assertIn(1, IlLiheap.benefit_amounts)
        self.assertIn(2, IlLiheap.benefit_amounts)
        self.assertIn(3, IlLiheap.benefit_amounts)
        self.assertIn(4, IlLiheap.benefit_amounts)
        self.assertIn(5, IlLiheap.benefit_amounts)
        self.assertIn(6, IlLiheap.benefit_amounts)

    def test_benefit_amount_for_single_person(self):
        """Test that benefit amount for 1 person is $315."""
        self.assertEqual(IlLiheap.benefit_amounts[1], 315)

    def test_benefit_amount_for_six_plus_people(self):
        """Test that benefit amount for 6+ people is $375."""
        self.assertEqual(IlLiheap.benefit_amounts[6], 375)

    def test_household_value_returns_zero_when_already_has_benefit(self):
        """Test that household_value returns 0 when already has IL LIHEAP."""
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=True)

        calculator = IlLiheap(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        result = calculator.household_value()

        self.assertEqual(result, 0)
        mock_screen.has_benefit.assert_called_once_with("il_liheap")

    def test_household_value_returns_zero_when_not_income_eligible(self):
        """Test that household_value returns 0 when not income eligible."""
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=False)

        calculator = IlLiheap(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_variable = Mock(return_value=False)

        result = calculator.household_value()

        self.assertEqual(result, 0)

    def test_household_value_returns_zero_when_no_qualifying_expenses(self):
        """Test that household_value returns 0 when no rent/mortgage expenses."""
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=False)
        mock_screen.has_expense = Mock(return_value=False)

        calculator = IlLiheap(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_variable = Mock(return_value=True)

        result = calculator.household_value()

        self.assertEqual(result, 0)
        mock_screen.has_expense.assert_called_once_with(["rent", "mortgage"])

    def test_household_value_returns_benefit_when_eligible(self):
        """Test that household_value returns correct benefit when eligible."""
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=False)
        mock_screen.has_expense = Mock(return_value=True)
        mock_screen.household_size = 3

        calculator = IlLiheap(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_variable = Mock(return_value=True)

        result = calculator.household_value()

        self.assertEqual(result, 340)  # Benefit for household size 3
