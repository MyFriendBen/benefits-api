"""TX tests."""

from programs.programs.cross_white_label.tanf.tx import TxTanf
from programs.framework.pe_dependencies.payload import pe_input
from programs.programs.testing_fixtures.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from programs.programs.cross_white_label.tanf.base import Tanf
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household
from programs.framework.pe_dependencies import irs_gross_income
from programs.framework.pe_dependencies import member
from programs.framework.pe_dependencies import spm


class TestTxTanfPeInput(TxPeInputTestBase):
    """Tests for TxTanf calculator pe_input dependencies."""

    def test_includes_tx_specific_dependencies(self):
        """Test that TxTanf includes TX-specific dependencies."""
        result = pe_input(self.screen, [TxTanf])
        household = result["household"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Income is provided at the person level so PE can apply the $120 work expense
        # deduction and 1/3 earned income disregard (§ 372.409) through its own formula.
        head_id = str(self.head.id)
        self.assertIn("employment_income", people[head_id])
        self.assertIn("self_employment_income", people[head_id])

        # TX state code
        self.assertIn("state_code", household_unit)

    def test_includes_pe_output_field(self):
        """Test that pe_input includes TxTanf pe_outputs."""
        result = pe_input(self.screen, [TxTanf])
        spm_unit = result["household"]["spm_units"]["spm_unit"]
        self.assertIn("tx_tanf", spm_unit)

    def test_includes_parent_tanf_dependencies(self):
        """Test that TxTanf includes dependencies from parent Tanf class."""
        result = pe_input(self.screen, [TxTanf])
        people = result["household"]["people"]
        head_id = str(self.head.id)

        self.assertIn("age", people[head_id])
        self.assertIn("is_full_time_college_student", people[head_id])

    def test_includes_tax_unit_dependent_dependency(self):
        """Test that TxTanf populates is_tax_unit_dependent for all members.

        This is required by PolicyEngine's tx_tanf_age_eligible_child formula, which
        gates child eligibility on is_tax_unit_dependent. Without it the field defaults
        to False and tx_tanf always returns $0.
        """
        result = pe_input(self.screen, [TxTanf])
        people = result["household"]["people"]

        for member in [self.head, self.spouse, self.child]:
            self.assertIn("is_tax_unit_dependent", people[str(member.id)])


class TestTxTanf(TestCase):
    """Tests for TxTanf (Temporary Assistance for Needy Families) calculator class."""

    def test_exists_and_is_subclass_of_tanf(self):
        """
        Test that TxTanf calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxTanf is a subclass of Tanf
        self.assertTrue(issubclass(TxTanf, Tanf))

        # Verify it has the expected properties
        self.assertEqual(TxTanf.pe_name, "tx_tanf")
        self.assertIsNotNone(TxTanf.pe_inputs)
        self.assertGreater(len(TxTanf.pe_inputs), 0)
        self.assertIsNotNone(TxTanf.pe_outputs)
        self.assertGreater(len(TxTanf.pe_outputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxTanf has all expected pe_inputs from parent and TX-specific.

        TxTanf should inherit all inputs from parent Tanf class plus add
        TX-specific dependencies like TxStateCodeDependency and income dependencies.
        """
        # TxTanf should have more inputs than the parent Tanf class
        self.assertGreater(len(TxTanf.pe_inputs), len(Tanf.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxTanf.pe_inputs)

        # Verify TaxUnitDependentDependency is present — required because PolicyEngine's
        # tx_tanf_age_eligible_child checks is_tax_unit_dependent to identify eligible
        # children in the TX certified group (§ 372.104 / 1-TAC-372-307).
        self.assertIn(member.TaxUnitDependentDependency, TxTanf.pe_inputs)

        # Verify person-level income dependencies are present so PE can apply the $120
        # work expense deduction and 1/3 earned income disregard (§ 372.409)
        for dep in irs_gross_income:
            self.assertIn(dep, TxTanf.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Tanf.pe_inputs:
            self.assertIn(parent_input, TxTanf.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX TANF inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxTanf.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

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
