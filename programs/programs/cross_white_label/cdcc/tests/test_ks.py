"""KS tests."""

from programs.programs.cross_white_label.cdcc.base import Cdcc
from programs.programs.cross_white_label.cdcc.ks import KsCdccFederal
from django.test import TestCase
from integrations.clients.policyengine.registry import all_calculators


class TestKsCdccFederal(TestCase):
    """ks_cdcc_federal registration against the shared federal Cdcc calculator.

    Distinct from ``ks_cdcc``, which is the Kansas credit and has its own class.
    """

    def test_is_the_federal_calculator_with_nothing_added(self):
        """Kansas has no state CDCC of its own beyond ``ks_cdcc``, so this must not
        diverge from the federal credit."""
        self.assertTrue(issubclass(KsCdccFederal, Cdcc))
        self.assertEqual(KsCdccFederal.pe_name, Cdcc.pe_name)
        self.assertEqual(list(KsCdccFederal.pe_inputs), list(Cdcc.pe_inputs))
        self.assertEqual(list(KsCdccFederal.pe_outputs), list(Cdcc.pe_outputs))

    def test_is_not_the_kansas_cdcc(self):
        """The federal and Kansas CDCC slugs resolve to different calculators."""
        self.assertIsNot(
            all_calculators["ks_cdcc_federal"],
            all_calculators["ks_cdcc"],
        )
