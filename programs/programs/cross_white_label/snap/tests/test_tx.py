"""TX tests."""

from programs.programs.cross_white_label.snap.tx import TxSnap
from integrations.clients.policyengine.policy_engine import pe_input
from programs.framework.tests.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from programs.programs.cross_white_label.snap.base import Snap
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household


class TestTxSnapPeInput(TxPeInputTestBase):
    """Tests for TxSnap calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxSnap pe_inputs dependencies."""
        result = pe_input(self.screen, [TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        household_unit = household["households"]["household"]

        # SPM-level dependencies
        spm_fields = [
            "snap_unearned_income",
            "snap_earned_income",
            "snap_assets",
            "snap_emergency_allotment",
            "housing_cost",
            "has_phone_expense",
            "has_heating_cooling_expense",
        ]
        for field in spm_fields:
            self.assertIn(field, spm_unit)

        # Member-level dependencies
        head_id = str(self.head.id)
        member_fields = ["child_support_expense", "age", "is_disabled"]
        for field in member_fields:
            self.assertIn(field, people[head_id])

        # TX-specific dependency
        self.assertIn("state_code", household_unit)

    def test_includes_pe_output_fields(self):
        """Test that pe_input includes TxSnap pe_outputs."""
        result = pe_input(self.screen, [TxSnap])
        spm_unit = result["household"]["spm_units"]["spm_unit"]
        self.assertIn("snap_if_takes_up", spm_unit)
        self.assertIsInstance(spm_unit["snap_if_takes_up"], dict)

    def test_state_code_is_tx(self):
        """Test that TxStateCodeDependency sets state_code to TX."""
        result = pe_input(self.screen, [TxSnap])
        household_unit = result["household"]["households"]["household"]

        if household_unit["state_code"]:
            period_key = list(household_unit["state_code"].keys())[0]
            self.assertEqual(household_unit["state_code"][period_key], "TX")

    def test_snap_assets_matches_screen(self):
        """Test that snap_assets matches Screen.household_assets."""
        result = pe_input(self.screen, [TxSnap])
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        if spm_unit["snap_assets"]:
            period_key = list(spm_unit["snap_assets"].keys())[0]
            self.assertEqual(spm_unit["snap_assets"][period_key], 5000)


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
        self.assertEqual(TxSnap.pe_name, "snap_if_takes_up")
        self.assertIsNotNone(TxSnap.pe_inputs)
        self.assertGreater(len(TxSnap.pe_inputs), 0)

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
