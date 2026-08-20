"""MO tests."""

from programs.programs.cross_white_label.ctc.base import Ctc
from programs.programs.cross_white_label.ctc.mo import MoCtc
from django.test import TestCase


class TestMoCtcWiring(TestCase):
    """mo_ctc registration against the shared federal Ctc calculator."""

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        MO has no state CTC, so ``mo_ctc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Ctc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(MoCtc, Ctc))
        self.assertEqual(MoCtc.pe_name, Ctc.pe_name)
        self.assertEqual(list(MoCtc.pe_inputs), list(Ctc.pe_inputs))
        self.assertEqual(list(MoCtc.pe_outputs), list(Ctc.pe_outputs))
