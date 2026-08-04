"""
Unit tests for the MO tax-unit PolicyEngine calculator registration (mo_ctc).

Missouri has no state CTC and no MO-specific variance, so ``mo_ctc`` maps
straight to the shared federal ``Ctc`` class rather than a subclass — the same
treatment as ``ks_ctc``, ``tx_ctc``, and ``wa_ctc``.

That makes registration the only MO-side fact to pin, and one part of it is
load-bearing: ``mo_tax_unit_calculators`` must be spread into the global
``all_tax_unit_calculators``. Missouri previously had no tax-unit calculators at
all, so the registry imported only its member and SPM dicts. Registering
``mo_ctc`` in ``mo_pe_calculators`` alone leaves it invisible to
``screener.views``, which resolves ``Program.name_abbreviated`` against
``all_calculators`` — the program would silently return no value.

Everything else about the calculator (``pe_name``, ``pe_outputs``, the input set,
and the absence of a state code) is a property of the shared federal class and is
asserted once in ``programs/programs/federal/pe/tests/test_tax.py``. Proving
``mo_ctc`` *is* that object extends those guarantees here.
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Ctc
from programs.programs.mo.pe import mo_pe_calculators, mo_tax_unit_calculators
from programs.programs.policyengine.calculators.registry import (
    all_calculators,
    all_tax_unit_calculators,
)


class TestMoCtcWiring(TestCase):
    """mo_ctc registration against the shared federal Ctc calculator."""

    def test_is_federal_ctc_everywhere(self):
        self.assertIs(mo_tax_unit_calculators["mo_ctc"], Ctc)
        self.assertIs(mo_pe_calculators["mo_ctc"], Ctc)
        self.assertIs(all_tax_unit_calculators["mo_ctc"], Ctc)
        self.assertIs(all_calculators["mo_ctc"], Ctc)

    def test_matches_builtin_federal_registry_key(self):
        """Same calculator the federal registry serves as ``ctc`` — no MO subclass."""
        self.assertIs(all_tax_unit_calculators["mo_ctc"], all_tax_unit_calculators["ctc"])
