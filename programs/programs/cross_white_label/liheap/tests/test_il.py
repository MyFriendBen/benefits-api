"""IL tests."""

from programs.programs.cross_white_label.liheap.il import IlLiheap
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from unittest.mock import MagicMock
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineSpmCalulator
from django.test import TestCase
from programs.framework.pe_dependencies import spm as spm_dependency


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
