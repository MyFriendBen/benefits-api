"""
Unit tests for IL tax-level PolicyEngine calculator classes.

These tests verify IL-specific calculator logic for tax-level programs including:
- Ileitc (Illinois Earned Income Tax Credit) calculator
- Ilctc (Illinois Child Tax Credit) calculator
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
from programs.programs.policyengine.calculators.dependencies import tax as tax_dependency
from programs.programs.policyengine.calculators.dependencies.household import IlStateCodeDependency
from programs.programs.federal.pe.tax import Eitc, Ctc
from programs.programs.il.pe import il_pe_calculators, il_tax_unit_calculators
from programs.programs.il.pe.tax import Ileitc, Ilctc


class TestIleitc(TestCase):
    """Tests for Illinois Earned Income Tax Credit calculator."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """Test that Ileitc is a subclass of PolicyEngineTaxUnitCalulator."""
        self.assertTrue(issubclass(Ileitc, PolicyEngineTaxUnitCalulator))

    def test_is_registered_in_il_pe_calculators(self):
        """Test that Ileitc is registered in the calculators dictionary."""
        self.assertIn("il_eitc", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_eitc"], Ileitc)

    def test_is_registered_in_il_tax_unit_calculators(self):
        """Test that Ileitc is registered in the tax calculators dictionary."""
        self.assertIn("il_eitc", il_tax_unit_calculators)
        self.assertEqual(il_tax_unit_calculators["il_eitc"], Ileitc)

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


class TestIlctc(TestCase):
    """Tests for Illinois Child Tax Credit calculator."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """Test that Ilctc is a subclass of PolicyEngineTaxUnitCalulator."""
        self.assertTrue(issubclass(Ilctc, PolicyEngineTaxUnitCalulator))

    def test_is_registered_in_il_pe_calculators(self):
        """Test that Ilctc is registered in the calculators dictionary."""
        self.assertIn("il_ctc", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_ctc"], Ilctc)

    def test_is_registered_in_il_tax_unit_calculators(self):
        """Test that Ilctc is registered in the tax calculators dictionary."""
        self.assertIn("il_ctc", il_tax_unit_calculators)
        self.assertEqual(il_tax_unit_calculators["il_ctc"], Ilctc)

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
