"""WA tests."""

from programs.programs.cross_white_label.ssi.base import Ssi
from django.test import TestCase
from programs.programs.cross_white_label.ssi.wa import WaSsi
from programs.framework.pe_dependencies.household import WaStateCodeDependency


class TestWaSsi(TestCase):
    """Tests for WaSsi calculator class wiring."""

    def test_exists_and_is_subclass_of_ssi(self):
        """WaSsi extends the federal Ssi PolicyEngine calculator."""
        self.assertTrue(issubclass(WaSsi, Ssi))

    def test_pe_name_is_ssi(self):
        """pe_name is inherited from Ssi and resolves to PolicyEngine's `ssi` variable."""
        self.assertEqual(WaSsi.pe_name, "ssi_if_takes_up")

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
