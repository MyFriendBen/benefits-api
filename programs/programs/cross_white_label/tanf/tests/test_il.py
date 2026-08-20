"""IL tests."""

from programs.framework.pe_dependencies.household import IlStateCodeDependency
from programs.programs.cross_white_label.tanf.il import IlTanf
from programs.programs.cross_white_label.tanf.base import Tanf
from django.test import TestCase
from programs.framework.pe_dependencies import spm as spm_dependency


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
