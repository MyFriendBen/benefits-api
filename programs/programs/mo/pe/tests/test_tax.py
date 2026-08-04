"""
Unit tests for the MO tax-unit PolicyEngine calculator registration (mo_ctc).

The Missouri Child Tax Credit entry is the federal Child Tax Credit used as-is:
Missouri has no state CTC and no MO-specific variance, so ``mo_ctc`` maps straight
to the shared federal ``Ctc`` class rather than a subclass. This mirrors how
``ks_ctc`` and ``wa_ctc`` are registered.

Because there is no MO subclass, the only MFB-side logic to pin is the registration
itself, and one part of it is load-bearing:

  - ``mo_tax_unit_calculators`` must be spread into the global
    ``all_tax_unit_calculators``. Missouri previously had no tax-unit calculators at
    all, so the registry imported only its member and SPM dicts. Registering
    ``mo_ctc`` in ``mo_pe_calculators`` alone leaves it invisible to
    ``screener.views``, which resolves ``Program.name_abbreviated`` against
    ``all_calculators`` — the program would silently return no value.

These tests pin that wiring so a future refactor can't drop it.
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Ctc
from programs.programs.mo.pe import mo_pe_calculators, mo_tax_unit_calculators
from programs.programs.policyengine.calculators.registry import (
    all_calculators,
    all_tax_unit_calculators,
)
import programs.programs.policyengine.calculators.dependencies as dependency


class TestMoCtcWiring(TestCase):
    """mo_ctc registration against the shared federal Ctc calculator."""

    def test_maps_to_the_shared_federal_ctc(self):
        """No MO variance, so mo_ctc is the federal class itself, not a subclass."""
        self.assertIs(mo_tax_unit_calculators["mo_ctc"], Ctc)

    def test_is_registered_in_mo_tax_unit_calculators(self):
        self.assertIn("mo_ctc", mo_tax_unit_calculators)

    def test_is_registered_in_mo_pe_calculators(self):
        self.assertIn("mo_ctc", mo_pe_calculators)
        self.assertIs(mo_pe_calculators["mo_ctc"], Ctc)

    def test_is_registered_in_the_global_registry(self):
        """screener.views matches Program.name_abbreviated against all_calculators keys,
        so the MO tax unit calculators must be spread into the global registry too."""
        self.assertIn("mo_ctc", all_tax_unit_calculators)
        self.assertIs(all_tax_unit_calculators["mo_ctc"], Ctc)
        self.assertIn("mo_ctc", all_calculators)
        self.assertIs(all_calculators["mo_ctc"], Ctc)

    def test_pe_name_is_ctc_value(self):
        """``ctc_value`` is the amount actually received after the credit is limited by
        tax liability plus the refundable portion, not the headline ``ctc``."""
        self.assertEqual(Ctc.pe_name, "ctc_value")

    def test_pe_outputs_are_the_ctc_dependency(self):
        self.assertEqual(Ctc.pe_outputs, [dependency.tax.Ctc])

    def test_pe_inputs_include_age_and_tax_unit_composition(self):
        """PE counts qualifying children from age and the dependent/spouse structure."""
        self.assertIn(dependency.member.AgeDependency, Ctc.pe_inputs)
        self.assertIn(dependency.member.TaxUnitDependentDependency, Ctc.pe_inputs)
        self.assertIn(dependency.member.TaxUnitSpouseDependency, Ctc.pe_inputs)

    def test_pe_inputs_include_irs_gross_income(self):
        """The credit phases out on income, so the gross income inputs must all be sent."""
        for income_input in dependency.irs_gross_income:
            self.assertIn(income_input, Ctc.pe_inputs)
