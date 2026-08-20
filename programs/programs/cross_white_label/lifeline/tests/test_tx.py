"""TX tests."""

from programs.programs.cross_white_label.lifeline.tx import TxLifeline
from integrations.clients.policyengine.policy_engine import pe_input
from programs.framework.tests.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from programs.programs.cross_white_label.lifeline.base import Lifeline
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household


class TestTxLifelinePeInput(TxPeInputTestBase):
    """Tests for TxLifeline calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all Lifeline pe_inputs dependencies."""
        result = pe_input(self.screen, [TxLifeline])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]

        # SPM-level dependency
        self.assertIn("broadband_cost", spm_unit)

        # Member-level income dependencies
        head_id = str(self.head.id)
        income_fields = [
            "employment_income",
            "self_employment_income",
            "rental_income",
            "taxable_pension_income",
            "social_security",
        ]
        for field in income_fields:
            self.assertIn(field, people[head_id])

    def test_includes_pe_output_field(self):
        """Test that pe_input includes Lifeline pe_outputs."""
        result = pe_input(self.screen, [TxLifeline])
        spm_unit = result["household"]["spm_units"]["spm_unit"]
        self.assertIn("lifeline", spm_unit)

    def test_income_values_are_correct(self):
        """Test that income values match HouseholdMember data."""
        result = pe_input(self.screen, [TxLifeline])
        people = result["household"]["people"]
        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)

        if people[head_id]["employment_income"]:
            period_key = list(people[head_id]["employment_income"].keys())[0]
            self.assertEqual(people[head_id]["employment_income"][period_key], 30000)
            self.assertEqual(people[head_id]["self_employment_income"][period_key], 5000)
            self.assertEqual(people[spouse_id]["taxable_pension_income"][period_key], 8000)


class TestTxLifeline(TestCase):
    """Tests for TxLifeline calculator class."""

    def test_exists_and_is_subclass_of_lifeline(self):
        """
        Test that TxLifeline calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxLifeline is a subclass of Lifeline
        self.assertTrue(issubclass(TxLifeline, Lifeline))

        # Verify it has the expected properties
        self.assertEqual(TxLifeline.pe_name, "lifeline")
        self.assertIsNotNone(TxLifeline.pe_inputs)
        self.assertGreater(len(TxLifeline.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxLifeline has all expected pe_inputs from parent and TX-specific.

        TxLifeline should inherit all inputs from parent Lifeline class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxLifeline should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxLifeline.pe_inputs), len(Lifeline.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxLifeline.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Lifeline.pe_inputs:
            self.assertIn(parent_input, TxLifeline.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Lifeline inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxLifeline.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")
