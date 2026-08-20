"""MO tests."""

from programs.programs.cross_white_label.cdcc.base import Cdcc
from programs.programs.cross_white_label.cdcc.mo import MoCdccFederal
from django.test import TestCase


class TestMoCdccFederalWiring(TestCase):
    """mo_cdcc_federal registration against the shared federal Cdcc calculator."""

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        Missouri has no state CDCC, so ``mo_cdcc_federal`` must not diverge from the
        federal credit. It is its own class only so the registry maps one key to one
        calculator — Kansas registers ``ks_cdcc_federal`` against ``KsCdccFederal``
        for the same reason. Asserting it overrides nothing is stricter than the
        cross-state identity this replaced: a subclass that added an input would
        still be a subclass, but would fail here.
        """
        self.assertTrue(issubclass(MoCdccFederal, Cdcc))
        self.assertEqual(MoCdccFederal.pe_name, Cdcc.pe_name)
        self.assertEqual(list(MoCdccFederal.pe_inputs), list(Cdcc.pe_inputs))
        self.assertEqual(list(MoCdccFederal.pe_outputs), list(Cdcc.pe_outputs))
