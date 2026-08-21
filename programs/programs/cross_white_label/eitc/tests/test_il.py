"""IL tests."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from programs.programs.cross_white_label.eitc.il import Ileitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from django.test import TestCase
from programs.framework.pe_dependencies import tax as tax_dependency


class TestIleitc(TestCase):
    """Tests for Illinois Earned Income Tax Credit calculator."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """Test that Ileitc is a subclass of PolicyEngineTaxUnitCalulator."""
        self.assertTrue(issubclass(Ileitc, PolicyEngineTaxUnitCalulator))

    def test_pe_name_is_il_eitc(self):
        """Test that pe_name is il_eitc."""
        self.assertEqual(Ileitc.pe_name, "il_eitc")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, Ileitc.pe_inputs)

    def test_pe_inputs_includes_federal_eitc_inputs(self):
        """Test that federal EITC inputs are included."""
        for parent_input in Eitc.pe_inputs:
            self.assertIn(parent_input, Ileitc.pe_inputs)

    def test_pe_outputs_includes_ileitc(self):
        """Test that Ileitc output is in pe_outputs."""
        self.assertIn(tax_dependency.Ileitc, Ileitc.pe_outputs)
