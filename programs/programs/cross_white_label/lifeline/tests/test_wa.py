"""WA tests."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
from django.test import TestCase
from programs.programs.cross_white_label.lifeline.wa import WaLifeline
from programs.framework.pe_dependencies.household import WaStateCodeDependency


class TestWaLifeline(TestCase):
    """Tests for WaLifeline calculator class."""

    def test_is_subclass_of_lifeline(self):
        """Test that WaLifeline is a subclass of federal Lifeline."""
        self.assertTrue(issubclass(WaLifeline, Lifeline))

    def test_pe_name_is_lifeline(self):
        """Test that pe_name is lifeline."""
        self.assertEqual(WaLifeline.pe_name, "lifeline")

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
