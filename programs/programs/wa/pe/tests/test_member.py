"""
Unit tests for WA member-level PolicyEngine calculator classes.

These tests verify WA-specific calculator wiring including:
- WaSsi calculator registration
- WA-specific pe_inputs (WaStateCodeDependency)
- Federal Ssi inputs are inherited

The eligibility math itself (FBR-minus-countable-income, the
$20 + $65 + 1/2 income exclusion stack, SGA cutoff, ISM (VTR/PMV) reductions,
and spousal/parental deeming) lives in PolicyEngine and is tested by
PolicyEngine's own test suite — not duplicated here. See
`programs/programs/wa/ssi/spec.md` for the 15 reference scenarios that the
end-to-end validation suite (`validations/.../wa_ssi.json`) exercises against
PolicyEngine via `python manage.py validate --program wa_ssi`.
"""

from django.test import TestCase

from programs.programs.federal.pe.member import Ssi
from programs.programs.policyengine.calculators.dependencies.household import WaStateCodeDependency
from programs.programs.wa.pe import wa_member_calculators, wa_pe_calculators
from programs.programs.wa.pe.member import WaSsi


class TestWaSsi(TestCase):
    """Tests for WaSsi calculator class wiring."""

    def test_exists_and_is_subclass_of_ssi(self):
        """WaSsi extends the federal Ssi PolicyEngine calculator."""
        self.assertTrue(issubclass(WaSsi, Ssi))

    def test_pe_name_is_ssi(self):
        """pe_name is inherited from Ssi and resolves to PolicyEngine's `ssi` variable."""
        self.assertEqual(WaSsi.pe_name, "ssi")

    def test_is_registered_in_wa_pe_calculators(self):
        """WaSsi is registered in the WA PE calculators dictionary as `wa_ssi`."""
        self.assertIn("wa_ssi", wa_pe_calculators)
        self.assertEqual(wa_pe_calculators["wa_ssi"], WaSsi)

    def test_is_registered_in_wa_member_calculators(self):
        """WaSsi is registered in the WA member-level subset (not SPM/tax)."""
        self.assertIn("wa_ssi", wa_member_calculators)
        self.assertEqual(wa_member_calculators["wa_ssi"], WaSsi)

    def test_pe_inputs_includes_wa_state_code_dependency(self):
        """The WA state code is added on top of the federal Ssi inputs."""
        self.assertIn(WaStateCodeDependency, WaSsi.pe_inputs)

    def test_wa_state_code_dependency_is_configured_correctly(self):
        """Sanity-check the dependency itself."""
        self.assertEqual(WaStateCodeDependency.state, "WA")
        self.assertEqual(WaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_all_parent_inputs(self):
        """All federal Ssi inputs flow through to WaSsi unchanged."""
        for parent_input in Ssi.pe_inputs:
            self.assertIn(parent_input, WaSsi.pe_inputs)

    def test_pe_inputs_has_more_than_parent(self):
        """WaSsi adds exactly one input on top of the parent (the WA state code)."""
        self.assertEqual(len(WaSsi.pe_inputs), len(Ssi.pe_inputs) + 1)

    def test_pe_outputs_inherited_from_ssi(self):
        """Output is the federal SSI dollar value (no override needed)."""
        self.assertEqual(WaSsi.pe_outputs, Ssi.pe_outputs)
