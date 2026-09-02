"""Recovered from pe/pe/tests."""

from django.test import TestCase
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.head_start.tx import TxHeadStart
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.early_head_start.tx import TxEarlyHeadStart


class TestTxHeadStartWiring(TestCase):
    """
    TX-specific wiring for Head Start (ages 3-5) and Early Head Start (birth-3 /
    pregnant). Both are thin wrappers on the federal calculators, adding only the
    TX state code.

    The shared contract (pe_name, pe_outputs, no federal input dropped, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for
    all registered subclasses in ``federal/pe/tests/test_head_start.py``.
    """

    def test_head_start_pe_inputs_includes_tx_state_code(self):
        self.assertTrue(issubclass(TxHeadStart, HeadStart))
        self.assertIn(TxStateCodeDependency, TxHeadStart.pe_inputs)

    def test_early_head_start_pe_inputs_includes_tx_state_code(self):
        self.assertTrue(issubclass(TxEarlyHeadStart, EarlyHeadStart))
        self.assertIn(TxStateCodeDependency, TxEarlyHeadStart.pe_inputs)
