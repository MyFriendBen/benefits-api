"""
Unit tests for the federal tax-unit PolicyEngine calculator ``Ctc``.

``Ctc`` is shared: Kansas, Missouri, Texas, and Washington all register their
own program slug (``ks_ctc``, ``mo_ctc``, ...) against this exact class object
rather than subclassing it, because the federal Child Tax Credit has no state
variance. That makes this class's wiring a cross-state contract — the properties
asserted here hold for every state that reuses it, so each state file only needs
to prove it points at this object (see e.g. ``TestMoCtcWiring``).

The eligibility math itself — the per-child maximum, the phase-out, the
refundable portion, and the limitation by tax liability — lives in PolicyEngine
and is covered by PolicyEngine's own test suite, not duplicated here.
"""

from django.test import TestCase

from programs.programs.federal.pe import federal_tax_unit_calculators
from programs.programs.federal.pe.tax import Ctc
from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
from programs.programs.policyengine.calculators.dependencies import (
    irs_gross_income,
    member,
    tax,
)
from programs.programs.policyengine.calculators.dependencies.household import StateCode
from programs.programs.policyengine.calculators.registry import (
    all_calculators,
    all_tax_unit_calculators,
)


class TestFederalCtc(TestCase):
    """Wiring of the shared federal Child Tax Credit calculator."""

    def test_is_a_tax_unit_calculator(self):
        self.assertTrue(issubclass(Ctc, PolicyEngineTaxUnitCalulator))

    def test_is_registered_as_ctc(self):
        self.assertIs(federal_tax_unit_calculators["ctc"], Ctc)
        self.assertIs(all_tax_unit_calculators["ctc"], Ctc)
        self.assertIs(all_calculators["ctc"], Ctc)

    def test_pe_name_is_ctc_value(self):
        """``ctc_value`` is the amount actually received — the credit after it is
        limited by tax liability plus the refundable portion — not the headline
        ``ctc``, which is the pre-limitation maximum."""
        self.assertEqual(Ctc.pe_name, "ctc_value")

    def test_pe_outputs_read_the_ctc_value_field(self):
        self.assertEqual(Ctc.pe_outputs, [tax.Ctc])
        self.assertEqual(tax.Ctc.field, "ctc_value")

    def test_pe_inputs_include_age_and_tax_unit_composition(self):
        """PolicyEngine counts qualifying children from age and the tax unit's
        dependent/spouse structure."""
        self.assertIn(member.AgeDependency, Ctc.pe_inputs)
        self.assertIn(member.TaxUnitDependentDependency, Ctc.pe_inputs)
        self.assertIn(member.TaxUnitSpouseDependency, Ctc.pe_inputs)

    def test_pe_inputs_include_irs_gross_income(self):
        """The credit phases out on income, so every gross income input is sent."""
        for income_input in irs_gross_income:
            self.assertIn(income_input, Ctc.pe_inputs)

    def test_pe_inputs_carry_no_state_code(self):
        """Nothing under PolicyEngine's ``gov/irs/credits/ctc`` variable tree reads
        ``state_code``, so no state's CTC should send one.

        Texas previously registered a ``TxCtc`` subclass that appended
        ``TxStateCodeDependency`` to these inputs. It changed no output — verified
        against live PE 1.779.3 across eight households — and was removed. This
        asserts the general case rather than one state's dependency, so a subclass
        for any state would have to fail it.

        Contrast ``co_ctc`` and ``il_ctc``: those are genuine *state* credits under
        ``gov/states/`` with their own calculators, and they do need a state code.
        """
        for pe_input in Ctc.pe_inputs:
            self.assertFalse(
                isinstance(pe_input, type) and issubclass(pe_input, StateCode),
                f"{pe_input.__name__} sends a state code to the federal CTC",
            )
