"""WA tests."""

from programs.programs.cross_white_label.ctc.base import Ctc
from django.test import TestCase
from programs.programs.cross_white_label.ctc.wa import WaCtc


class TestWaCtc(TestCase):
    """`wa_ctc` reuses the federal Ctc calculator unchanged (same class object).

    The calculator's own properties (`pe_name`, `pe_outputs`, the input set, and
    the absence of a state code) are asserted once in
    `programs/programs/cross_white_label/ctc/tests/test_federal.py`.
    """

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        WA has no state CTC, so ``wa_ctc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Ctc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(WaCtc, Ctc))
        self.assertEqual(WaCtc.pe_name, Ctc.pe_name)
        self.assertEqual(list(WaCtc.pe_inputs), list(Ctc.pe_inputs))
        self.assertEqual(list(WaCtc.pe_outputs), list(Ctc.pe_outputs))
