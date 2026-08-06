"""
Unit tests for the MO tax-unit PolicyEngine calculator registrations.

Missouri has no state CTC or state EITC and no MO-specific variance, so
``mo_ctc`` and ``mo_eitc`` map straight to the shared federal ``Ctc`` and
``Eitc`` classes rather than subclasses — the same treatment as ``ks_ctc``,
``tx_ctc``/``tx_eitc``, and ``wa_ctc``/``wa_eitc``.

That makes registration the only MO-side fact to pin, and one part of it is
load-bearing: ``mo_tax_unit_calculators`` must be spread into the global
``all_tax_unit_calculators`` in ``registry.py``. ``screener.views`` resolves
``Program.name_abbreviated`` against ``all_calculators``, so a program registered
only in ``mo_pe_calculators`` is invisible to it and silently returns no value.

Everything else about the calculators (``pe_name``, ``pe_outputs``, the input set,
and the absence of a state code) is a property of the shared federal classes and
is asserted once in ``programs/programs/federal/pe/tests/test_tax.py``. Proving
these slugs *are* those objects extends those guarantees here.
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Ctc, Eitc
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


class TestMoEitcWiring(TestCase):
    """mo_eitc registration against the shared federal Eitc calculator."""

    def test_is_federal_eitc_everywhere(self):
        self.assertIs(mo_tax_unit_calculators["mo_eitc"], Eitc)
        self.assertIs(mo_pe_calculators["mo_eitc"], Eitc)
        self.assertIs(all_tax_unit_calculators["mo_eitc"], Eitc)
        self.assertIs(all_calculators["mo_eitc"], Eitc)

    def test_matches_builtin_federal_registry_key(self):
        """Same calculator the federal registry serves as ``eitc`` — no MO subclass."""
        self.assertIs(all_tax_unit_calculators["mo_eitc"], all_tax_unit_calculators["eitc"])
