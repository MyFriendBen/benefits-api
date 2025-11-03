"""
Unit tests for TX SPM (Supplemental Poverty Measure) PolicyEngine calculator classes.

These tests verify TX-specific SNAP calculator logic including:
- Calculator registration
- TX-specific pe_inputs (TxStateCodeDependency)

Note: Tests for Screen.has_benefit() have been moved to screener/tests/test_models.py
as they test Screen model methods, not TX-specific SNAP logic.
"""

from django.test import TestCase

from programs.programs.tx.pe import tx_pe_calculators
from programs.programs.tx.pe.spm import TxSnap
from programs.programs.federal.pe.spm import Snap
from programs.programs.policyengine.calculators.dependencies import household
from programs.programs.policyengine.calculators.dependencies.household import TxStateCodeDependency


class TestTxSnap(TestCase):
    """Tests for TxSnap calculator class."""

    def test_exists_and_is_subclass_of_snap(self):
        """
        Test that TxSnap calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxSnap is a subclass of Snap
        self.assertTrue(issubclass(TxSnap, Snap))

        # Verify it has the expected properties
        self.assertEqual(TxSnap.pe_name, "snap")
        self.assertIsNotNone(TxSnap.pe_inputs)
        self.assertGreater(len(TxSnap.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX SNAP is registered in the calculators dictionary."""
        # Verify tx_snap is in the calculators dictionary
        self.assertIn("tx_snap", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_snap"], TxSnap)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxSnap has all expected pe_inputs from parent and TX-specific.

        TxSnap should inherit all inputs from parent Snap class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxSnap should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxSnap.pe_inputs), len(Snap.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxSnap.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Snap.pe_inputs:
            self.assertIn(parent_input, TxSnap.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX SNAP inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxSnap.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")
