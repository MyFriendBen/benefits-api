"""TX tests."""

from programs.framework.pe_dependencies.constants import MAIN_TAX_UNIT
from programs.programs.cross_white_label.aca.tx import TxAca
from integrations.clients.policyengine.policy_engine import pe_input
from programs.programs.testing.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from programs.programs.cross_white_label.aca.base import Aca
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household


class TestTxAcaPeInput(TxPeInputTestBase):
    """Tests for TxAca calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxAca pe_inputs dependencies."""
        result = pe_input(self.screen, [TxAca])
        household = result["household"]
        tax_units = household["tax_units"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # Tax unit exists
        self.assertIn(MAIN_TAX_UNIT, tax_units)

        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        # Member-level dependencies
        self.assertIn("age", people[head_id])
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("is_disabled", people[head_id])
        self.assertIn("is_tax_unit_head", people[head_id])
        self.assertIn("is_tax_unit_spouse", people[spouse_id])
        self.assertIn("is_tax_unit_dependent", people[child_id])

        # Income dependencies
        self.assertIn("employment_income", people[head_id])

        # Household-level dependencies
        self.assertIn("zip_code", household_unit)
        self.assertIn("state_code", household_unit)

    def test_includes_pe_output_field(self):
        """Test that pe_input includes TxAca pe_outputs."""
        result = pe_input(self.screen, [TxAca])
        tax_units = result["household"]["tax_units"]

        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("aca_ptc", tax_units[MAIN_TAX_UNIT])

    def test_zipcode_is_populated(self):
        """Test that zipcode is correctly populated."""
        result = pe_input(self.screen, [TxAca])
        household_unit = result["household"]["households"]["household"]

        if household_unit["zip_code"]:
            period_key = list(household_unit["zip_code"].keys())[0]
            self.assertEqual(household_unit["zip_code"][period_key], "78701")

    def test_income_values_are_correct(self):
        """Test that income values are correctly populated."""
        result = pe_input(self.screen, [TxAca])
        people = result["household"]["people"]
        head_id = str(self.head.id)

        if people[head_id]["employment_income"]:
            period_key = list(people[head_id]["employment_income"].keys())[0]
            self.assertEqual(people[head_id]["employment_income"][period_key], 30000)
            self.assertEqual(people[head_id]["self_employment_income"][period_key], 5000)
            self.assertEqual(people[head_id]["rental_income"][period_key], 12000)


class TestTxAca(TestCase):
    """Tests for TxAca calculator class."""

    def test_exists_and_is_subclass_of_aca(self):
        """
        Test that TxAca calculator class exists and inherits from Aca.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxAca has the expected properties
        self.assertEqual(TxAca.pe_name, "aca_ptc")
        self.assertIsNotNone(TxAca.pe_inputs)
        self.assertGreater(len(TxAca.pe_inputs), 0)

        # Verify it inherits from Aca
        self.assertTrue(issubclass(TxAca, Aca))

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxAca has all expected pe_inputs from parent and TX-specific.

        TxAca should inherit all inputs from parent Aca class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxAca should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxAca.pe_inputs), len(Aca.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxAca.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Aca.pe_inputs:
            self.assertIn(parent_input, TxAca.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX ACA inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxAca.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_name_matches_federal_aca(self):
        """
        Test that TxAca uses the same pe_name as federal ACA.

        Since this is the federal ACA Premium Tax Credit program for Texas residents,
        it should use the same PolicyEngine name as the federal calculator.
        """
        self.assertEqual(TxAca.pe_name, "aca_ptc")
        self.assertEqual(TxAca.pe_name, Aca.pe_name)

    def test_pe_outputs_inherits_from_federal_aca(self):
        """
        Test that TxAca uses the same pe_outputs as federal ACA.

        The outputs should be the same since this is calculating
        the federal ACA Premium Tax Credit benefit amount.
        """
        self.assertEqual(TxAca.pe_outputs, Aca.pe_outputs)
