"""
Unit tests for WA tax-level PolicyEngine calculator classes.

These tests verify WA-specific calculator wiring including:
- `wa_ctc` aliases the federal Child Tax Credit class (`programs.programs.federal.pe.tax.Ctc`)
  with no WA-specific wrapper
- WaWftc calculator registration (in wa_pe_calculators, wa_tax_calculators,
  and the global PE tax-unit registry)
- WA-specific pe_inputs (`WaStateCodeDependency`) on `WaEitc`/`WaWftc` only;
  federal `Eitc` inputs are inherited by those classes

The eligibility math itself (federal EITC phase-in/phase-out, MFJ adjustments,
investment-income cap, the 25-64 age floor for childless filers, qualifying-
child rules, and the WA-specific scaling + $50 minimum-credit floor) lives in
PolicyEngine and is tested by PolicyEngine's own test suite — not duplicated
here. See `programs/programs/wa/wftc/spec.md` for the 9 reference scenarios
that the end-to-end validation suite (`validations/.../wa_wftc.json`)
exercises against PolicyEngine via `python manage.py validate --program wa_wftc`.
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Ctc, Eitc
from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
from programs.programs.policyengine.calculators.dependencies import tax as tax_dependency
from programs.programs.policyengine.calculators.dependencies.household import WaStateCodeDependency
from programs.programs.policyengine.calculators.registry import all_tax_unit_calculators
from programs.programs.wa.pe import wa_pe_calculators, wa_tax_calculators
from programs.programs.wa.pe.tax import WaEitc, WaWftc


class TestWaEitc(TestCase):
    """Tests for WaEitc calculator class wiring."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """WaEitc is a `PolicyEngineTaxUnitCalulator` (lives in the tax-unit entity)."""
        self.assertTrue(issubclass(WaEitc, PolicyEngineTaxUnitCalulator))

    def test_pe_name_targets_eitc(self):
        """`pe_name` resolves to PolicyEngine's `eitc` variable."""
        self.assertEqual(WaEitc.pe_name, "eitc")

    def test_is_registered_in_wa_pe_calculators(self):
        """WaEitc is registered in the WA PE calculators dictionary as `wa_eitc`."""
        self.assertIn("wa_eitc", wa_pe_calculators)
        self.assertEqual(wa_pe_calculators["wa_eitc"], WaEitc)

    def test_is_registered_in_wa_tax_calculators(self):
        """WaEitc is registered in the WA tax-unit subset (not member/SPM)."""
        self.assertIn("wa_eitc", wa_tax_calculators)
        self.assertEqual(wa_tax_calculators["wa_eitc"], WaEitc)

    def test_is_registered_in_global_tax_unit_registry(self):
        """WaEitc flows up into the global PE tax-unit registry (so the engine sees it)."""
        self.assertIn("wa_eitc", all_tax_unit_calculators)
        self.assertEqual(all_tax_unit_calculators["wa_eitc"], WaEitc)

    def test_pe_inputs_includes_wa_state_code_dependency(self):
        """The WA state code is added on top of the federal Eitc inputs."""
        self.assertIn(WaStateCodeDependency, WaEitc.pe_inputs)

    def test_pe_inputs_includes_all_federal_eitc_inputs(self):
        """All federal Eitc inputs flow through to WaEitc unchanged."""
        for parent_input in Eitc.pe_inputs:
            self.assertIn(parent_input, WaEitc.pe_inputs)

    def test_pe_inputs_adds_exactly_one_dependency_to_eitc(self):
        """WaEitc adds exactly one input on top of federal Eitc (the WA state code)."""
        self.assertEqual(len(WaEitc.pe_inputs), len(Eitc.pe_inputs) + 1)

    def test_pe_outputs_is_eitc(self):
        """Output is the federal EITC dollar value."""
        self.assertEqual(WaEitc.pe_outputs, [tax_dependency.Eitc])

    def test_eitc_tax_dependency_targets_correct_field(self):
        """The Eitc tax dependency points at PE's `eitc` field."""
        self.assertEqual(tax_dependency.Eitc.field, "eitc")


class TestWaCtc(TestCase):
    """`wa_ctc` reuses the federal Ctc calculator unchanged (same class object)."""

    def test_wa_ctc_is_federal_ctc_everywhere(self):
        """Washington registers the WA program slug against the federal class."""
        self.assertIs(wa_tax_calculators["wa_ctc"], Ctc)
        self.assertIs(wa_pe_calculators["wa_ctc"], Ctc)
        self.assertIs(all_tax_unit_calculators["wa_ctc"], Ctc)

    def test_wa_ctc_matches_builtin_federal_registry_key(self):
        """Same calculator as global `ctc` — no WA-specific subclass."""
        self.assertEqual(all_tax_unit_calculators["wa_ctc"], all_tax_unit_calculators["ctc"])

    def test_wa_ctc_pe_inputs_exclude_washington_state_dependency(self):
        """Federal CTC wiring has no WA state-code input (unlike WA EITC / WFTC)."""
        self.assertNotIn(WaStateCodeDependency, Ctc.pe_inputs)

    def test_pe_name_and_outputs_match_federal_ctc(self):
        self.assertEqual(Ctc.pe_name, "ctc_value")
        self.assertEqual(Ctc.pe_outputs, [tax_dependency.Ctc])
        self.assertEqual(tax_dependency.Ctc.field, "ctc_value")


class TestWaWftc(TestCase):
    """Tests for WaWftc calculator class wiring."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """WaWftc is a `PolicyEngineTaxUnitCalulator` (lives in the tax-unit entity)."""
        self.assertTrue(issubclass(WaWftc, PolicyEngineTaxUnitCalulator))

    def test_pe_name_targets_wa_working_families_tax_credit(self):
        """`pe_name` resolves to PolicyEngine's `wa_working_families_tax_credit` variable."""
        self.assertEqual(WaWftc.pe_name, "wa_working_families_tax_credit")

    def test_is_registered_in_wa_pe_calculators(self):
        """WaWftc is registered in the WA PE calculators dictionary as `wa_wftc`."""
        self.assertIn("wa_wftc", wa_pe_calculators)
        self.assertEqual(wa_pe_calculators["wa_wftc"], WaWftc)

    def test_is_registered_in_wa_tax_calculators(self):
        """WaWftc is registered in the WA tax-unit subset (not member/SPM)."""
        self.assertIn("wa_wftc", wa_tax_calculators)
        self.assertEqual(wa_tax_calculators["wa_wftc"], WaWftc)

    def test_is_registered_in_global_tax_unit_registry(self):
        """WaWftc flows up into the global PE tax-unit registry (so the engine sees it)."""
        self.assertIn("wa_wftc", all_tax_unit_calculators)
        self.assertEqual(all_tax_unit_calculators["wa_wftc"], WaWftc)

    def test_pe_inputs_includes_wa_state_code_dependency(self):
        """The WA state code is added on top of the federal Eitc inputs."""
        self.assertIn(WaStateCodeDependency, WaWftc.pe_inputs)

    def test_wa_state_code_dependency_is_configured_correctly(self):
        """Sanity-check the dependency itself."""
        self.assertEqual(WaStateCodeDependency.state, "WA")
        self.assertEqual(WaStateCodeDependency.field, "state_code")

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
