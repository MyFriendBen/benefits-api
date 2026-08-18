"""
Unit tests for the KS tax-unit PolicyEngine calculators that reuse federal classes.

Kansas registers two program slugs against the federal calculators unchanged:
``ks_ctc`` and ``ks_cdcc_federal``. Each has a thin KS subclass — ``KsCtc`` and
``KsCdccFederal`` — that overrides nothing, so the registry can map one key to one
class. The KS-side facts to pin are that each slug resolves to its own subclass and
that neither subclass diverges from its federal parent.

The calculators' own properties (``pe_name``, ``pe_outputs``, the input set, and
the absence of a state code) belong to the shared classes; the CTC set is
asserted once in ``programs/programs/federal/pe/tests/test_tax.py``. Proving the
KS slugs *are* those objects extends those guarantees here.

``ks_eitc`` and ``ks_cdcc`` are genuine Kansas credits with their own calculators
and are not covered by this module.
"""

from django.test import TestCase
from programs.programs.ks.pe.tax import KsCdccFederal, KsCtc

from programs.programs.federal.pe.tax import Cdcc, Ctc
from programs.programs.ks.pe import ks_pe_calculators, ks_tax_unit_calculators
from integrations.clients.policyengine.registry import (
    all_calculators,
    all_tax_unit_calculators,
)


class TestKsCtc(TestCase):
    """ks_ctc registration against the shared federal Ctc calculator."""

    def test_is_federal_ctc_everywhere(self):
        self.assertIs(ks_tax_unit_calculators["ks_ctc"], KsCtc)
        self.assertIs(ks_pe_calculators["ks_ctc"], KsCtc)
        self.assertIs(all_tax_unit_calculators["ks_ctc"], KsCtc)
        self.assertIs(all_calculators["ks_ctc"], KsCtc)

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
            all_tax_unit_calculators["ks_cdcc_federal"],
            all_tax_unit_calculators["ks_cdcc"],
        )
