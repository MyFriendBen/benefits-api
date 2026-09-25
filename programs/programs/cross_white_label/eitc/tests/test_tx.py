"""TX tests."""

from programs.programs.cross_white_label.eitc.base import Eitc
from django.test import TestCase
from programs.programs.cross_white_label.eitc.tx import TxEitc


class TestTxEitc(TestCase):
    """tx_eitc registration against the shared federal Eitc calculator.

    The federal EITC has no Texas variance, so the slug maps to the shared class
    with no TX subclass. Its own properties are asserted once in
    ``programs/programs/cross_white_label/eitc/tests/test_federal.py``.
    """

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        TX has no state EITC, so ``tx_eitc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Eitc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(TxEitc, Eitc))
        self.assertEqual(TxEitc.pe_name, Eitc.pe_name)
        self.assertEqual(list(TxEitc.pe_inputs), list(Eitc.pe_inputs))
        self.assertEqual(list(TxEitc.pe_outputs), list(Eitc.pe_outputs))
