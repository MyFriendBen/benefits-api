"""KS tests."""

from programs.programs.cross_white_label.ctc.base import Ctc
from programs.programs.cross_white_label.ctc.ks import KsCtc
from django.test import TestCase


class TestKsCtc(TestCase):
    """ks_ctc registration against the shared federal Ctc calculator."""

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        KS has no state CTC, so ``ks_ctc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Ctc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(KsCtc, Ctc))
        self.assertEqual(KsCtc.pe_name, Ctc.pe_name)
        self.assertEqual(list(KsCtc.pe_inputs), list(Ctc.pe_inputs))
        self.assertEqual(list(KsCtc.pe_outputs), list(Ctc.pe_outputs))
