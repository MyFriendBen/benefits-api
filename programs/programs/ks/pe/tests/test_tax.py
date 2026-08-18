"""
Unit tests for the KS tax-unit PolicyEngine calculators that reuse federal classes.

Kansas registers two program slugs against shared federal calculators unchanged:
``ks_ctc`` against ``Ctc`` (no state CTC in Kansas) and ``ks_cdcc_federal``
against ``Cdcc``. Neither has a KS subclass, so registration is the only KS-side
fact to pin.

The calculators' own properties (``pe_name``, ``pe_outputs``, the input set, and
the absence of a state code) belong to the shared classes; the CTC set is
asserted once in ``programs/programs/federal/pe/tests/test_tax.py``. Proving the
KS slugs *are* those objects extends those guarantees here.

``ks_eitc`` and ``ks_cdcc`` are genuine Kansas credits with their own calculators
and are not covered by this module.
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Cdcc, Ctc
from programs.programs.ks.pe import ks_pe_calculators, ks_tax_unit_calculators
from integrations.clients.policyengine.registry import (
    all_calculators,
    all_tax_unit_calculators,
)


class TestKsCtc(TestCase):
    """ks_ctc registration against the shared federal Ctc calculator."""

    def test_is_federal_ctc_everywhere(self):
        self.assertIs(ks_tax_unit_calculators["ks_ctc"], Ctc)
        self.assertIs(ks_pe_calculators["ks_ctc"], Ctc)
        self.assertIs(all_tax_unit_calculators["ks_ctc"], Ctc)
        self.assertIs(all_calculators["ks_ctc"], Ctc)

    def test_matches_builtin_federal_registry_key(self):
        """Same calculator the federal registry serves as ``ctc`` — no KS subclass."""
        self.assertIs(all_tax_unit_calculators["ks_ctc"], all_tax_unit_calculators["ctc"])


class TestKsCdccFederal(TestCase):
    """ks_cdcc_federal registration against the shared federal Cdcc calculator.

    Distinct from ``ks_cdcc``, which is the Kansas credit and has its own class.
    """

    def test_is_federal_cdcc_everywhere(self):
        self.assertIs(ks_tax_unit_calculators["ks_cdcc_federal"], Cdcc)
        self.assertIs(ks_pe_calculators["ks_cdcc_federal"], Cdcc)
        self.assertIs(all_tax_unit_calculators["ks_cdcc_federal"], Cdcc)
        self.assertIs(all_calculators["ks_cdcc_federal"], Cdcc)

    def test_is_not_the_kansas_cdcc(self):
        """The federal and Kansas CDCC slugs resolve to different calculators."""
        self.assertIsNot(
            all_tax_unit_calculators["ks_cdcc_federal"],
            all_tax_unit_calculators["ks_cdcc"],
        )
