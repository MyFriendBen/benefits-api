"""TX tests."""

from django.test import TestCase

from programs.programs.cross_white_label.ssi.base import Ssi
from programs.programs.cross_white_label.ssi.tx import TxSsi
from programs.framework.pe_dependencies.household import TxStateCodeDependency


class TestTxSsi(TestCase):
    """Tests for TxSsi calculator class."""

    def test_adds_nothing_but_the_state_code(self):
        """PE models the TX state supplement from the state code alone."""
        self.assertEqual(set(TxSsi.pe_inputs) - set(Ssi.pe_inputs), {TxStateCodeDependency})
