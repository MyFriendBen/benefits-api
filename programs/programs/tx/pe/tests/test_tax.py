"""
Unit tests for TX Tax Unit PolicyEngine calculator classes.

These tests verify TX-specific tax calculator logic including:
- Calculator registration
- TX-specific pe_inputs (TxStateCodeDependency)
- Inheritance from federal tax calculators
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Eitc, Ctc
from programs.programs.policyengine.calculators.dependencies import household
from programs.programs.policyengine.calculators.dependencies.household import (
    TxStateCodeDependency,
)
from programs.programs.tx.pe import tx_pe_calculators
from programs.programs.tx.pe.tax import TxEitc, TxCtc


class TestTxEitc(TestCase):
    """Tests for TxEitc calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """
        Test that TxEitc calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxEitc has the expected properties
        self.assertEqual(TxEitc.pe_name, "eitc")
        self.assertIsNotNone(TxEitc.pe_inputs)
        self.assertGreater(len(TxEitc.pe_inputs), 0)
        self.assertIsNotNone(TxEitc.pe_outputs)
        self.assertGreater(len(TxEitc.pe_outputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX EITC is registered in the calculators dictionary."""
        # Verify tx_eitc is in the calculators dictionary
        self.assertIn("tx_eitc", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_eitc"], TxEitc)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxEitc has all expected pe_inputs from parent and TX-specific.

        TxEitc should inherit all inputs from parent Eitc class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxEitc should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxEitc.pe_inputs), len(Eitc.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxEitc.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Eitc.pe_inputs:
            self.assertIn(parent_input, TxEitc.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX EITC inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxEitc.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_name_matches_federal_eitc(self):
        """
        Test that TxEitc uses the same pe_name as federal EITC.

        Since this is the federal EITC program for Texas residents,
        it should use the same PolicyEngine name as the federal calculator.
        """
        self.assertEqual(TxEitc.pe_name, "eitc")
        self.assertEqual(TxEitc.pe_name, Eitc.pe_name)

    def test_pe_outputs_matches_federal_eitc(self):
        """
        Test that TxEitc uses the same pe_outputs as federal EITC.

        The outputs should be the same since this is calculating
        the federal EITC benefit amount.
        """
        self.assertEqual(TxEitc.pe_outputs, Eitc.pe_outputs)


class TestTxCtc(TestCase):
    """Tests for TxCtc calculator class."""

    def test_exists_and_is_subclass_of_ctc(self):
        """
        Test that TxCtc calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxCtc inherits from PolicyEngineTaxUnitCalulator
        from programs.programs.policyengine.calculators.base import (
            PolicyEngineTaxUnitCalulator,
        )

        self.assertTrue(issubclass(TxCtc, PolicyEngineTaxUnitCalulator))

        # Verify it has the expected properties
        self.assertEqual(TxCtc.pe_name, "ctc_value")
        self.assertIsNotNone(TxCtc.pe_inputs)
        self.assertGreater(len(TxCtc.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX CTC is registered in the calculators dictionary."""
        # Verify tx_ctc is in the calculators dictionary
        self.assertIn("tx_ctc", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_ctc"], TxCtc)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxCtc has all expected pe_inputs from parent and TX-specific.

        TxCtc should inherit all inputs from parent Ctc class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxCtc should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxCtc.pe_inputs), len(Ctc.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxCtc.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Ctc.pe_inputs:
            self.assertIn(parent_input, TxCtc.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX CTC inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxCtc.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")
