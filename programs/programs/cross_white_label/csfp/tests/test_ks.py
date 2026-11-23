"""
Unit tests for KsCsfp PolicyEngine calculator class.

These tests verify KS-specific calculator wiring for CSFP:
- KsCsfp calculator registration and configuration
- KS state code and county, which PolicyEngine's county gate reads
- The inputs PolicyEngine's categorical routes read (reported receipt, MSP's income)
"""

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_dependencies.household import KsCountyDependency, KsStateCodeDependency
from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
from programs.programs.cross_white_label.csfp.ks import KsCsfp
from programs.programs.cross_white_label.msp.base import Msp


class TestKsCsfp(TestCase):
    """Tests for KsCsfp calculator class."""

    def test_exists_and_is_subclass_of_csfp(self):
        self.assertTrue(issubclass(KsCsfp, CommoditySupplementalFoodProgram))
        self.assertEqual(KsCsfp.program_code, "ks_csfp")
        self.assertEqual(KsCsfp.pe_name, "commodity_supplemental_food_program")

    def test_pe_inputs_includes_all_parent_inputs(self):
        for parent_input in CommoditySupplementalFoodProgram.pe_inputs:
            self.assertIn(parent_input, KsCsfp.pe_inputs)

    def test_pe_inputs_includes_ks_state_code_dependency(self):
        self.assertIn(KsStateCodeDependency, KsCsfp.pe_inputs)
        self.assertEqual(KsStateCodeDependency.state, "KS")

    def test_pe_inputs_includes_ks_county_dependency(self):
        """Without it PolicyEngine defaults to a county with no site and denies statewide."""
        self.assertIn(KsCountyDependency, KsCsfp.pe_inputs)
        self.assertEqual(KsCountyDependency.state_dependency_class, KsStateCodeDependency)

    def test_pe_inputs_includes_receipt_contract(self):
        """Holds the SSI and SNAP routes to reported receipt instead of simulated benefits."""
        for receipt_input in dependency.receipt_contract:
            self.assertIn(receipt_input, KsCsfp.pe_inputs)

    def test_pe_inputs_includes_msp_inputs(self):
        """The MSP route reads PolicyEngine's computed msp, which needs MSP's own inputs."""
        for msp_input in Msp.pe_inputs:
            self.assertIn(msp_input, KsCsfp.pe_inputs)

    def test_has_same_pe_outputs_as_parent(self):
        self.assertEqual(KsCsfp.pe_outputs, CommoditySupplementalFoodProgram.pe_outputs)
