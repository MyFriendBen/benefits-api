"""IL tests."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
from programs.programs.cross_white_label.lifeline.il import IlLifeline
from django.test import TestCase
import programs.framework.pe_dependencies as dependency


class TestIlLifelineWiring(TestCase):
    """IlLifeline registration and IL-specific pe_inputs handling."""

    def test_is_subclass_of_lifeline(self):
        self.assertTrue(issubclass(IlLifeline, Lifeline))

    def test_program_code_is_state_scoped(self):
        """The bare ``lifeline`` code belongs to the base class, which must not back a row."""
        self.assertEqual(IlLifeline.program_code, "il_lifeline")

    def test_pe_name_is_lifeline(self):
        """The federal SPM-level variable; IL adds no state variable of its own."""
        self.assertEqual(IlLifeline.pe_name, "lifeline")

    def test_pe_outputs_are_inherited_from_lifeline(self):
        self.assertEqual(IlLifeline.pe_outputs, [dependency.spm.Lifeline])

    # --- the IL-specific input ---

    def test_pe_inputs_includes_il_state_code(self):
        """``pe_input()`` never sends state_code on its own, and PE's Lifeline chain
        branches on it for both the state supplement and the income limit."""
        self.assertIn(dependency.household.IlStateCodeDependency, IlLifeline.pe_inputs)

    def test_il_state_code_dependency_sends_il(self):
        self.assertEqual(dependency.household.IlStateCodeDependency.state, "IL")

    # --- federal inputs must survive the IL override ---

    def test_pe_inputs_retains_all_federal_inputs(self):
        for federal_input in Lifeline.pe_inputs:
            self.assertIn(federal_input, IlLifeline.pe_inputs)

    def test_pe_inputs_adds_exactly_the_state_code(self):
        added = [d for d in IlLifeline.pe_inputs if d not in Lifeline.pe_inputs]
        self.assertEqual(added, [dependency.household.IlStateCodeDependency])
