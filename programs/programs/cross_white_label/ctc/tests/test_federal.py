"""FEDERAL tests."""

from programs.programs.cross_white_label.ctc.base import Ctc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.framework.pe_dependencies.household import StateCode
from django.test import TestCase
from programs.framework.pe_dependencies import irs_gross_income
from programs.framework.pe_dependencies import member
from programs.framework.pe_dependencies import tax
from integrations.clients.policyengine.policy_engine import pe_input


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
