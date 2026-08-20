"""TX tests."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
from django.test import TestCase
from programs.programs.cross_white_label.medicaid.emergency.tx import TxEmergencyMedicaid
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household


class TestTxEmergencyMedicaid(TestCase):
    """Tests for TxEmergencyMedicaid calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxEmergencyMedicaid calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxEmergencyMedicaid is a subclass of Medicaid
        self.assertTrue(issubclass(TxEmergencyMedicaid, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxEmergencyMedicaid.pe_name, "medicaid")
        self.assertIsNotNone(TxEmergencyMedicaid.pe_inputs)
        self.assertGreater(len(TxEmergencyMedicaid.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxEmergencyMedicaid has all expected pe_inputs from parent and TX-specific.

        TxEmergencyMedicaid should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxEmergencyMedicaid should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxEmergencyMedicaid.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxEmergencyMedicaid.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxEmergencyMedicaid.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Emergency Medicaid inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxEmergencyMedicaid.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxEmergencyMedicaid has the same pe_outputs as parent Medicaid class."""
        # TxEmergencyMedicaid should use the same outputs as parent
        self.assertEqual(TxEmergencyMedicaid.pe_outputs, Medicaid.pe_outputs)
