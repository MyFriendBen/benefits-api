"""
Unit tests for WA SPM-level PolicyEngine calculator classes.

These tests verify WA-specific calculator logic including:
- WaLifeline calculator registration
- WaSnap calculator registration
- WA-specific pe_inputs (WaStateCodeDependency)
"""

from django.test import TestCase

from programs.programs.federal.pe.spm import Lifeline, Snap
from programs.programs.policyengine.calculators.dependencies.household import WaStateCodeDependency
from programs.programs.wa.pe import wa_pe_calculators, wa_spm_calculators
from programs.programs.wa.pe.spm import WaLifeline, WaSnap


class TestWaSnap(TestCase):
    """Tests for WaSnap calculator class."""

    def test_exists_and_is_subclass_of_snap(self):
        """Test that WaSnap is a subclass of federal Snap."""
        self.assertTrue(issubclass(WaSnap, Snap))

    def test_pe_name_is_snap(self):
        """Test that pe_name is snap."""
        self.assertEqual(WaSnap.pe_name, "snap")

    def test_is_registered_in_wa_pe_calculators(self):
        """Test that WaSnap is registered in the calculators dictionary."""
        self.assertIn("wa_snap", wa_pe_calculators)
        self.assertEqual(wa_pe_calculators["wa_snap"], WaSnap)

    def test_is_registered_in_wa_spm_calculators(self):
        """Test that WaSnap is registered in the SPM calculators dictionary."""
        self.assertIn("wa_snap", wa_spm_calculators)
        self.assertEqual(wa_spm_calculators["wa_snap"], WaSnap)

    def test_pe_inputs_includes_wa_state_code_dependency(self):
        """Test that WaStateCodeDependency is in pe_inputs."""
        self.assertIn(WaStateCodeDependency, WaSnap.pe_inputs)

    def test_wa_state_code_dependency_is_configured_correctly(self):
        """Test that WaStateCodeDependency sets state to WA."""
        self.assertEqual(WaStateCodeDependency.state, "WA")
        self.assertEqual(WaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_all_parent_inputs(self):
        """Test that all parent Snap inputs are included in WaSnap."""
        for parent_input in Snap.pe_inputs:
            self.assertIn(parent_input, WaSnap.pe_inputs)

    def test_pe_inputs_has_more_than_parent(self):
        """Test that WaSnap has more inputs than the parent Snap class."""
        self.assertGreater(len(WaSnap.pe_inputs), len(Snap.pe_inputs))


class TestWaLifeline(TestCase):
    """Tests for WaLifeline calculator class."""

    def test_is_subclass_of_lifeline(self):
        """Test that WaLifeline is a subclass of federal Lifeline."""
        self.assertTrue(issubclass(WaLifeline, Lifeline))

    def test_pe_name_is_lifeline(self):
        """Test that pe_name is lifeline."""
        self.assertEqual(WaLifeline.pe_name, "lifeline")

    def test_is_registered_in_wa_pe_calculators(self):
        """Test that WaLifeline is registered in the calculators dictionary."""
        self.assertIn("wa_lifeline", wa_pe_calculators)
        self.assertEqual(wa_pe_calculators["wa_lifeline"], WaLifeline)

    def test_is_registered_in_wa_spm_calculators(self):
        """Test that WaLifeline is registered in the SPM calculators dictionary."""
        self.assertIn("wa_lifeline", wa_spm_calculators)
        self.assertEqual(wa_spm_calculators["wa_lifeline"], WaLifeline)

    def test_pe_inputs_includes_wa_state_code_dependency(self):
        """Test that WaStateCodeDependency is in pe_inputs."""
        self.assertIn(WaStateCodeDependency, WaLifeline.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """Test that all parent Lifeline inputs are included in WaLifeline."""
        for parent_input in Lifeline.pe_inputs:
            self.assertIn(parent_input, WaLifeline.pe_inputs)

    def test_pe_inputs_has_more_than_parent(self):
        """Test that WaLifeline has more inputs than the parent Lifeline class."""
        self.assertGreater(len(WaLifeline.pe_inputs), len(Lifeline.pe_inputs))
