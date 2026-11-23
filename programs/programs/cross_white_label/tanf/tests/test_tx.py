"""TX tests."""

from programs.programs.cross_white_label.tanf.tx import TxTanf
from django.test import TestCase
from programs.framework.pe_dependencies import irs_gross_income
from programs.framework.pe_dependencies import member
from programs.framework.pe_dependencies import spm


class TestTxTanf(TestCase):
    """Tests for TxTanf (Temporary Assistance for Needy Families) calculator class."""

    def test_pe_inputs_includes_tax_unit_dependent_dependency(self):
        """
        Test that TaxUnitDependentDependency is in TxTanf pe_inputs.

        PolicyEngine's tx_tanf_age_eligible_child formula requires is_tax_unit_dependent
        to identify eligible children in the TX certified group (per § 372.104 /
        1-TAC-372-307). Without this dependency, is_tax_unit_dependent defaults to
        False for all members, causing tx_tanf_eligible to always be False and the
        program to return $0 for every household.

        Other states (CO, IL, NC) use the federal is_demographic_tanf_eligible check
        which only requires age and pregnancy — no is_tax_unit_dependent needed. TX is
        unique in explicitly modeling the certified group composition this way.
        """
        self.assertIn(member.TaxUnitDependentDependency, TxTanf.pe_inputs)
        self.assertEqual(member.TaxUnitDependentDependency.field, "is_tax_unit_dependent")

    def test_pe_inputs_includes_person_level_income_dependencies(self):
        """
        Test that person-level income dependencies are in TxTanf pe_inputs.

        TX TANF income eligibility uses two tests (§ 372.408):
          - Budgetary needs test: income after $120 work expense < budgetary needs standard
          - Recognizable needs test: income after work expense + 1/3 disregard < 25% of standard

        Providing income at the person level (employment_income, self_employment_income, etc.)
        lets PolicyEngine apply the work expense deduction and earned income disregard through
        its own formula chain. The previous approach of passing gross income directly as
        tx_tanf_countable_earned_income bypassed these deductions, causing households with
        gross wages between ~$188-$402/month (family of 3, 1 parent) to be incorrectly denied.
        """
        for dep in irs_gross_income:
            self.assertIn(dep, TxTanf.pe_inputs)

    def test_pe_outputs_includes_tx_tanf(self):
        """
        Test that TxTanf output dependency is properly configured.

        The calculator should output the tx_tanf variable to PolicyEngine.
        """
        # Verify TxTanf output dependency is in pe_outputs
        self.assertIn(spm.TxTanf, TxTanf.pe_outputs)
        self.assertEqual(spm.TxTanf.field, "tx_tanf")
