"""TX tests."""

from programs.programs.cross_white_label.aca.tx import TxAca
from django.test import TestCase
from programs.programs.cross_white_label.aca.base import Aca


class TestTxAca(TestCase):
    """Tests for TxAca calculator class."""

    def test_pe_name_matches_federal_aca(self):
        """
        Test that TxAca uses the same pe_name as federal ACA.

        Since this is the federal ACA Premium Tax Credit program for Texas residents,
        it should use the same PolicyEngine name as the federal calculator.
        """
        self.assertEqual(TxAca.pe_name, "aca_ptc")
        self.assertEqual(TxAca.pe_name, Aca.pe_name)

    def test_pe_outputs_inherits_from_federal_aca(self):
        """
        Test that TxAca uses the same pe_outputs as federal ACA.

        The outputs should be the same since this is calculating
        the federal ACA Premium Tax Credit benefit amount.
        """
        self.assertEqual(TxAca.pe_outputs, Aca.pe_outputs)
