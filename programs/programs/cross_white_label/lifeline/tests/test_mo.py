"""MO tests."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
from programs.programs.cross_white_label.lifeline.mo import MoLifeline
from django.test import TestCase
import programs.framework.pe_dependencies as dependency


class TestMoLifelineWiring(TestCase):
    """MoLifeline registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_lifeline(self):
        self.assertTrue(issubclass(MoLifeline, Lifeline))

    def test_pe_name_is_lifeline(self):
        """The federal SPM-level variable; MO adds no state variable of its own."""
        self.assertEqual(MoLifeline.pe_name, "lifeline")

    def test_pe_outputs_are_inherited_from_lifeline(self):
        self.assertEqual(MoLifeline.pe_outputs, [dependency.spm.Lifeline])

    # --- the MO-specific input ---

    def test_pe_inputs_includes_mo_state_code(self):
        """``pe_input()`` never sends state_code on its own; PE's Lifeline chain reads
        it for both the state supplement branch and the TX FPG expansion."""
        self.assertIn(dependency.household.MoStateCodeDependency, MoLifeline.pe_inputs)

    def test_mo_state_code_dependency_sends_mo(self):
        self.assertEqual(dependency.household.MoStateCodeDependency.state, "MO")

    # --- federal inputs must survive the MO override ---

    def test_pe_inputs_retains_all_federal_inputs(self):
        for federal_input in Lifeline.pe_inputs:
            self.assertIn(federal_input, MoLifeline.pe_inputs)

    def test_pe_inputs_includes_broadband_and_phone_cost(self):
        """PE caps the benefit at combined phone + broadband cost, so both are needed
        or an eligible household's value collapses toward $0."""
        self.assertIn(dependency.spm.BroadbandCostDependency, MoLifeline.pe_inputs)
        self.assertIn(dependency.spm.PhoneCostDependency, MoLifeline.pe_inputs)

    def test_pe_inputs_adds_exactly_one_input_over_federal(self):
        """Fed (as-is): the state code is the only MO addition."""
        self.assertEqual(len(MoLifeline.pe_inputs), len(Lifeline.pe_inputs) + 1)
