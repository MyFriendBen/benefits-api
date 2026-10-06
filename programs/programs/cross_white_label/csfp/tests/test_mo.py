"""
Unit tests for MoCsfp PolicyEngine calculator class.

These tests verify MO-specific calculator wiring for CSFP:
- MoCsfp calculator registration and configuration
- MO state code, and no county input (PolicyEngine has no Missouri county gate)
"""

from django.test import TestCase

from programs.framework.pe_dependencies.household import CountyDependency, MoStateCodeDependency
from programs.framework.pe_dependencies.spm import CsfpCountableIncomeDependency
from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
from programs.programs.cross_white_label.csfp.mo import MoCsfp


class TestMoCsfp(TestCase):
    """Tests for MoCsfp calculator class."""

    def test_exists_and_is_subclass_of_csfp(self):
        self.assertTrue(issubclass(MoCsfp, CommoditySupplementalFoodProgram))
        self.assertEqual(MoCsfp.program_code, "mo_csfp")
        self.assertEqual(MoCsfp.pe_name, "commodity_supplemental_food_program")

    def test_pe_inputs_includes_all_parent_inputs(self):
        for parent_input in CommoditySupplementalFoodProgram.pe_inputs:
            self.assertIn(parent_input, MoCsfp.pe_inputs)

    def test_pe_inputs_includes_mo_state_code_dependency(self):
        self.assertIn(MoStateCodeDependency, MoCsfp.pe_inputs)
        self.assertEqual(MoStateCodeDependency.state, "MO")

    def test_pe_inputs_sends_csfp_countable_income(self):
        """Missouri counts workers' comp, alimony and investment income, which PolicyEngine's
        own CSFP source list omits, so the all-types total is supplied."""
        self.assertIn(CsfpCountableIncomeDependency, MoCsfp.pe_inputs)

    def test_pe_inputs_declares_no_county(self):
        self.assertFalse(any(issubclass(Data, CountyDependency) for Data in MoCsfp.pe_inputs))

    def test_has_same_pe_outputs_as_parent(self):
        self.assertEqual(MoCsfp.pe_outputs, CommoditySupplementalFoodProgram.pe_outputs)
