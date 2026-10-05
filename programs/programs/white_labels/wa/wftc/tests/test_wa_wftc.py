"""WA WFTC tests."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from django.test import TestCase
from programs.programs.white_labels.wa.wftc.calculator import WaWftc
from programs.framework.pe_dependencies import tax as tax_dependency


class TestWaWftc(TestCase):
    """Tests for WaWftc calculator class wiring."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """WaWftc is a `PolicyEngineTaxUnitCalulator` (lives in the tax-unit entity)."""
        self.assertTrue(issubclass(WaWftc, PolicyEngineTaxUnitCalulator))

    def test_pe_name_targets_wa_working_families_tax_credit(self):
        """`pe_name` resolves to PolicyEngine's `wa_working_families_tax_credit` variable."""
        self.assertEqual(WaWftc.pe_name, "wa_working_families_tax_credit")

    def test_pe_inputs_includes_all_federal_eitc_inputs(self):
        """All federal Eitc inputs flow through to WaWftc unchanged."""
        for parent_input in Eitc.pe_inputs:
            self.assertIn(parent_input, WaWftc.pe_inputs)

    def test_pe_inputs_adds_exactly_one_dependency_to_eitc(self):
        """WaWftc adds exactly one input on top of federal Eitc (the WA state code)."""
        self.assertEqual(len(WaWftc.pe_inputs), len(Eitc.pe_inputs) + 1)

    def test_pe_outputs_is_wa_wftc(self):
        """Output is the WA WFTC dollar value (not the federal EITC)."""
        self.assertEqual(WaWftc.pe_outputs, [tax_dependency.WaWftc])

    def test_wa_wftc_tax_dependency_targets_correct_field(self):
        """The WaWftc tax dependency points at PE's `wa_working_families_tax_credit` field."""
        self.assertEqual(tax_dependency.WaWftc.field, "wa_working_families_tax_credit")
