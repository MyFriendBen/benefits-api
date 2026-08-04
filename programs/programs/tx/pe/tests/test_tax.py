"""
Unit tests for TX Tax Unit PolicyEngine calculator classes.

These tests verify TX-specific tax calculator logic including:
- Calculator registration
- TX-specific pe_inputs (TxStateCodeDependency)
- Inheritance from federal tax calculators
"""

from django.test import TestCase

from programs.programs.federal.pe.tax import Eitc, Ctc, Aca
from programs.programs.policyengine.calculators.dependencies import household
from programs.programs.policyengine.calculators.dependencies.household import (
    TxStateCodeDependency,
)
from programs.programs.policyengine.calculators.registry import (
    all_calculators,
    all_tax_unit_calculators,
)
from programs.programs.tx.pe import tx_pe_calculators, tx_tax_unit_calculators
from programs.programs.tx.pe.tax import TxEitc, TxAca


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
    """tx_ctc registration against the shared federal Ctc calculator.

    Texas previously registered a ``TxCtc`` subclass that appended
    ``TxStateCodeDependency``. The federal CTC reads no state variable, so that
    input changed no output — verified against live PE 1.779.3 across eight
    households — and the subclass was removed in favor of the shared class.

    The calculator's own properties (``pe_name``, ``pe_outputs``, the input set,
    and the absence of a state code) are asserted once in
    ``programs/programs/federal/pe/tests/test_tax.py``.
    """

    def test_is_federal_ctc_everywhere(self):
        self.assertIs(tx_tax_unit_calculators["tx_ctc"], Ctc)
        self.assertIs(tx_pe_calculators["tx_ctc"], Ctc)
        self.assertIs(all_tax_unit_calculators["tx_ctc"], Ctc)
        self.assertIs(all_calculators["tx_ctc"], Ctc)

    def test_matches_builtin_federal_registry_key(self):
        """Same calculator the federal registry serves as ``ctc`` — no TX subclass."""
        self.assertIs(all_tax_unit_calculators["tx_ctc"], all_tax_unit_calculators["ctc"])


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

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX ACA is registered in the calculators dictionary."""
        # Verify tx_aca is in the calculators dictionary
        self.assertIn("tx_aca", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_aca"], TxAca)

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
