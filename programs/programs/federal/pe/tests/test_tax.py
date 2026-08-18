"""
Unit tests for the shared federal tax-unit PolicyEngine calculators.

``Ctc`` and ``Eitc`` are shared: states register their own program slug
(``ks_ctc``, ``mo_ctc``, ``mo_eitc``, ...) against these exact class objects
rather than subclassing them, because neither federal credit has state variance.
That makes each class's wiring a cross-state contract — the properties asserted
here hold for every state that reuses it, so a state file only needs to prove it
points at this object (see e.g. ``TestMoCtcWiring``).

Neither federal credit reads ``state_code``: there is no state reference
anywhere under PolicyEngine's ``gov/irs/credits/ctc`` or
``gov/irs/credits/earned_income`` variable trees. ``test_pe_inputs_carry_no_state_code``
pins that generically for both.

The eligibility math itself — phase-ins, phase-outs, per-child maximums, the
refundable portions, and the investment-income cap — lives in PolicyEngine and is
covered by PolicyEngine's own test suite, not duplicated here.
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Ctc, Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.framework.pe_dependencies import (
    irs_gross_income,
    member,
    tax,
)
from programs.framework.pe_dependencies.household import StateCode


class TestFederalCtc(TestCase):
    """Wiring of the shared federal Child Tax Credit calculator."""

    def test_is_a_tax_unit_calculator(self):
        self.assertTrue(issubclass(Ctc, PolicyEngineTaxUnitCalulator))

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
        ``state_code``, so no state's CTC sends one — a state code here would be an
        input the formula ignores.

        Asserted against the ``StateCode`` base class rather than one state's
        dependency, so a subclass adding any state's code fails this.

        Contrast ``co_ctc`` and ``il_ctc``: those are genuine *state* credits under
        ``gov/states/`` with their own calculators, and they do need a state code.
        """
        for pe_input in Ctc.pe_inputs:
            self.assertFalse(
                isinstance(pe_input, type) and issubclass(pe_input, StateCode),
                f"{pe_input.__name__} sends a state code to the federal CTC",
            )


class TestFederalEitc(TestCase):
    """Wiring of the shared federal Earned Income Tax Credit calculator."""

    def test_is_a_tax_unit_calculator(self):
        self.assertTrue(issubclass(Eitc, PolicyEngineTaxUnitCalulator))

    def test_pe_name_is_eitc(self):
        self.assertEqual(Eitc.pe_name, "eitc")

    def test_pe_outputs_read_the_eitc_field(self):
        self.assertEqual(Eitc.pe_outputs, [tax.Eitc])
        self.assertEqual(tax.Eitc.field, "eitc")

    def test_pe_inputs_include_age_and_tax_unit_composition(self):
        """Age drives the 25-64 rule for childless filers; the dependent/spouse
        structure drives the qualifying-child count and the joint-filer thresholds."""
        self.assertIn(member.AgeDependency, Eitc.pe_inputs)
        self.assertIn(member.TaxUnitDependentDependency, Eitc.pe_inputs)
        self.assertIn(member.TaxUnitSpouseDependency, Eitc.pe_inputs)

    def test_pe_inputs_include_irs_gross_income(self):
        """The credit phases in and back out on income, so every gross income
        input is sent."""
        for income_input in irs_gross_income:
            self.assertIn(income_input, Eitc.pe_inputs)

    def test_pe_inputs_carry_no_state_code(self):
        """Nothing under PolicyEngine's ``gov/irs/credits/earned_income`` variable
        tree reads ``state_code``, so no state's federal EITC sends one — a state
        code here would be an input the formula ignores.

        Asserted against the ``StateCode`` base class rather than one state's
        dependency, so a subclass adding any state's code fails this.

        Contrast ``co_eitc``, ``il_eitc``, ``ks_total_eitc``, and ``ma_eitc``: those
        are genuine *state* EITCs under ``gov/states/`` with their own calculators,
        and they do need a state code.
        """
        for pe_input in Eitc.pe_inputs:
            self.assertFalse(
                isinstance(pe_input, type) and issubclass(pe_input, StateCode),
                f"{pe_input.__name__} sends a state code to the federal EITC",
            )
