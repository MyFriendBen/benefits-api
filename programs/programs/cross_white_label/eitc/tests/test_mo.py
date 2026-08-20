"""MO tests."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.eitc.mo import MoEitc
from django.test import TestCase


class TestMoEitcWiring(TestCase):
    """mo_eitc registration against the shared federal Eitc calculator."""

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        MO has no state EITC, so ``mo_eitc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Eitc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(MoEitc, Eitc))
        self.assertEqual(MoEitc.pe_name, Eitc.pe_name)
        self.assertEqual(list(MoEitc.pe_inputs), list(Eitc.pe_inputs))
        self.assertEqual(list(MoEitc.pe_outputs), list(Eitc.pe_outputs))
