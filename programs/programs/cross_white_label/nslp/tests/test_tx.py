"""TX tests."""

from programs.programs.cross_white_label.nslp.base import SchoolLunch
from django.test import TestCase
from programs.programs.cross_white_label.nslp.tx import TxNslp
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household


class TestTxNslp(TestCase):
    """Tests for TxNslp (National School Lunch Program) calculator class."""

    def test_exists_and_is_subclass_of_school_lunch(self):
        """
        Test that TxNslp calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxNslp is a subclass of SchoolLunch
        self.assertTrue(issubclass(TxNslp, SchoolLunch))

        # Verify it has the expected properties from parent
        self.assertEqual(TxNslp.pe_name, "school_meal_net_subsidy")
        self.assertIsNotNone(TxNslp.pe_inputs)
        self.assertGreater(len(TxNslp.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxNslp has all expected pe_inputs from parent and TX-specific.

        TxNslp should inherit all inputs from parent SchoolLunch class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxNslp should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxNslp.pe_inputs), len(SchoolLunch.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxNslp.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in SchoolLunch.pe_inputs:
            self.assertIn(parent_input, TxNslp.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX NSLP inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxNslp.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")
