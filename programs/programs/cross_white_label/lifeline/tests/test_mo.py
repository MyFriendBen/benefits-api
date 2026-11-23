"""MO tests."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
from programs.programs.cross_white_label.lifeline.mo import MoLifeline
from django.test import TestCase


class TestMoLifelineWiring(TestCase):
    """MoLifeline registration and MO-specific pe_inputs handling."""

    def test_pe_name_is_lifeline(self):
        """The federal SPM-level variable; MO adds no state variable of its own."""
        self.assertEqual(MoLifeline.pe_name, "lifeline")

    # --- federal inputs must survive the MO override ---

    def test_pe_inputs_adds_exactly_one_input_over_federal(self):
        """Fed (as-is): the state code is the only MO addition."""
        self.assertEqual(len(MoLifeline.pe_inputs), len(Lifeline.pe_inputs) + 1)
