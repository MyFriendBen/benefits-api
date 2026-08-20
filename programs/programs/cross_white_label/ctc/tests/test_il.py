"""IL tests."""

from programs.programs.cross_white_label.ctc.base import Ctc
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from programs.programs.cross_white_label.ctc.il import Ilctc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from django.test import TestCase
from programs.framework.pe_dependencies import tax as tax_dependency


class TestIlctc(TestCase):
    """Tests for Illinois Child Tax Credit calculator."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """Test that Ilctc is a subclass of PolicyEngineTaxUnitCalulator."""
        self.assertTrue(issubclass(Ilctc, PolicyEngineTaxUnitCalulator))

    def test_pe_name_is_il_ctc(self):
        """Test that pe_name is il_ctc."""
        self.assertEqual(Ilctc.pe_name, "il_ctc")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, Ilctc.pe_inputs)

    def test_pe_inputs_includes_federal_ctc_inputs(self):
        """Test that federal CTC inputs are included."""
        for parent_input in Ctc.pe_inputs:
            self.assertIn(parent_input, Ilctc.pe_inputs)

    def test_pe_outputs_includes_ilctc(self):
        """Test that Ilctc output is in pe_outputs."""
        self.assertIn(tax_dependency.Ilctc, Ilctc.pe_outputs)
