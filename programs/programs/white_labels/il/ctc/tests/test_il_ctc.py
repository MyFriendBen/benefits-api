"""IL tests."""

from programs.programs.white_labels.il.ctc.calculator import Ilctc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from django.test import TestCase
from programs.framework.pe_dependencies import ctc_inputs
from programs.framework.pe_dependencies import tax as tax_dependency


class TestIlctc(TestCase):
    """Tests for Illinois Child Tax Credit calculator."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """Test that Ilctc is a subclass of PolicyEngineTaxUnitCalulator."""
        self.assertTrue(issubclass(Ilctc, PolicyEngineTaxUnitCalulator))

    def test_pe_name_is_il_ctc(self):
        """Test that pe_name is il_ctc."""
        self.assertEqual(Ilctc.pe_name, "il_ctc")

    def test_pe_inputs_includes_the_shared_ctc_inputs(self):
        """Test that the shared child tax credit inputs are included."""
        for shared_input in ctc_inputs:
            self.assertIn(shared_input, Ilctc.pe_inputs)

    def test_pe_outputs_includes_ilctc(self):
        """Test that Ilctc output is in pe_outputs."""
        self.assertIn(tax_dependency.Ilctc, Ilctc.pe_outputs)
