"""
Unit tests for WA member-level PolicyEngine calculator classes.

Mirrors the TX SSI tests in programs/programs/tx/pe/tests/test_member.py and
verifies WA-specific calculator wiring (state code dependency, registration,
inheritance from the federal Ssi calculator).
"""

from django.test import TestCase

from programs.programs.federal.pe.member import Ssi
from programs.programs.policyengine.calculators.dependencies import household
from programs.programs.policyengine.calculators.dependencies.household import WaStateCodeDependency
from programs.programs.wa.pe import wa_pe_calculators, wa_member_calculators
from programs.programs.wa.pe.member import WaSsi


class TestWaSsi(TestCase):
    """Tests for WaSsi calculator class."""

    def test_exists_and_is_subclass_of_ssi(self):
        """
        Test that WaSsi calculator class exists and is a subclass of the
        federal Ssi calculator (which sets pe_name="ssi").
        """
        self.assertTrue(issubclass(WaSsi, Ssi))
        self.assertEqual(WaSsi.pe_name, "ssi")
        self.assertIsNotNone(WaSsi.pe_inputs)
        self.assertGreater(len(WaSsi.pe_inputs), 0)

    def test_is_registered_in_wa_pe_calculators(self):
        """Test that WA SSI is registered under name_abbreviated 'wa_ssi'."""
        self.assertIn("wa_ssi", wa_member_calculators)
        self.assertIn("wa_ssi", wa_pe_calculators)
        self.assertEqual(wa_pe_calculators["wa_ssi"], WaSsi)

    def test_is_registered_in_global_registry(self):
        """Test that WA SSI is exposed via the cross-state PolicyEngine registry."""
        from programs.programs.policyengine.calculators.registry import (
            all_calculators,
            all_member_calculators,
        )

        self.assertIn("wa_ssi", all_member_calculators)
        self.assertIn("wa_ssi", all_calculators)
        self.assertEqual(all_member_calculators["wa_ssi"], WaSsi)

    def test_pe_inputs_includes_all_parent_inputs_plus_wa_specific(self):
        """
        WaSsi should inherit all inputs from parent Ssi class plus add
        WaStateCodeDependency.
        """
        self.assertGreater(len(WaSsi.pe_inputs), len(Ssi.pe_inputs))
        self.assertIn(household.WaStateCodeDependency, WaSsi.pe_inputs)
        for parent_input in Ssi.pe_inputs:
            self.assertIn(parent_input, WaSsi.pe_inputs)

    def test_pe_inputs_includes_wa_state_code_dependency(self):
        """
        WaStateCodeDependency must be in pe_inputs and configured with
        state="WA" so PolicyEngine evaluates SSI under Washington rules.
        """
        self.assertIn(WaStateCodeDependency, WaSsi.pe_inputs)
        self.assertEqual(WaStateCodeDependency.state, "WA")
        self.assertEqual(WaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_ssi_member_dependencies(self):
        """Spot-check that key SSI member dependencies are inherited."""
        from programs.programs.policyengine.calculators.dependencies.member import (
            AgeDependency,
            IsBlindDependency,
            IsDisabledDependency,
            SsiCountableResourcesDependency,
            SsiEarnedIncomeDependency,
            SsiReportedDependency,
            SsiUnearnedIncomeDependency,
        )

        for dep in (
            SsiCountableResourcesDependency,
            SsiReportedDependency,
            IsBlindDependency,
            IsDisabledDependency,
            SsiEarnedIncomeDependency,
            SsiUnearnedIncomeDependency,
            AgeDependency,
        ):
            self.assertIn(dep, WaSsi.pe_inputs)

    def test_has_same_pe_outputs_as_parent(self):
        """WaSsi keeps the federal Ssi outputs (PolicyEngine returns the SSI amount)."""
        self.assertEqual(WaSsi.pe_outputs, Ssi.pe_outputs)
