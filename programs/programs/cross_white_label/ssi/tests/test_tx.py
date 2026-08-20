"""TX tests."""

from programs.programs.cross_white_label.ssi.tx import TxSsi
from integrations.clients.policyengine.policy_engine import pe_input
from programs.programs.testing.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from programs.programs.cross_white_label.ssi.base import Ssi
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household


class TestTxSsiPeInput(TxPeInputTestBase):
    """Tests for TxSsi calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxSsi pe_inputs dependencies."""
        result = pe_input(self.screen, [TxSsi])
        people = result["household"]["people"]
        head_id = str(self.head.id)

        # SSI-specific member dependencies
        ssi_fields = [
            "ssi_countable_resources",
            "ssi",
            "receives_ssi",
            "takes_up_ssi_if_eligible",
            "is_blind",
            "is_disabled",
            "ssi_earned_income",
            "ssi_unearned_income",
            "age",
        ]
        for field in ssi_fields:
            self.assertIn(field, people[head_id])

    def test_includes_pe_output_field(self):
        """Test that pe_input includes TxSsi pe_outputs."""
        result = pe_input(self.screen, [TxSsi])
        people = result["household"]["people"]
        head_id = str(self.head.id)

        self.assertIn("ssi_if_takes_up", people[head_id])
        self.assertIsInstance(people[head_id]["ssi_if_takes_up"], dict)

    def test_disability_fields_populated(self):
        """Test that disability fields are populated correctly."""
        result = pe_input(self.screen, [TxSsi])
        people = result["household"]["people"]

        head = people[str(self.head.id)]
        spouse = people[str(self.spouse.id)]

        self.assertIn("is_disabled", head)
        self.assertIn("is_disabled", spouse)
        self.assertIn("is_blind", head)


class TestTxSsi(TestCase):
    """Tests for TxSsi calculator class."""

    def test_exists_and_is_subclass_of_ssi(self):
        """
        Test that TxSsi calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxSsi is a subclass of Ssi
        self.assertTrue(issubclass(TxSsi, Ssi))

        # Verify it has the expected properties
        self.assertEqual(TxSsi.pe_name, "ssi_if_takes_up")
        self.assertIsNotNone(TxSsi.pe_inputs)
        self.assertGreater(len(TxSsi.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxSsi has all expected pe_inputs from parent and TX-specific.

        TxSsi should inherit all inputs from parent Ssi class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxSsi should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxSsi.pe_inputs), len(Ssi.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxSsi.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Ssi.pe_inputs:
            self.assertIn(parent_input, TxSsi.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX SSI inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxSsi.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_ssi_countable_resources_dependency(self):
        """Test that TxSsi inherits SsiCountableResourcesDependency from parent Ssi class."""
        from programs.framework.pe_dependencies.member import (
            SsiCountableResourcesDependency,
        )

        self.assertIn(SsiCountableResourcesDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_the_receipt_contract(self):
        """TxSsi inherits the reported-amount and take-up inputs from the federal Ssi class."""
        from programs.framework.pe_dependencies import receipt_contract

        for dep in receipt_contract:
            self.assertIn(dep, TxSsi.pe_inputs)

    def test_pe_inputs_includes_is_blind_dependency(self):
        """Test that TxSsi inherits IsBlindDependency from parent Ssi class."""
        from programs.framework.pe_dependencies.member import IsBlindDependency

        self.assertIn(IsBlindDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_is_disabled_dependency(self):
        """Test that TxSsi inherits IsDisabledDependency from parent Ssi class."""
        from programs.framework.pe_dependencies.member import IsDisabledDependency

        self.assertIn(IsDisabledDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_ssi_earned_income_dependency(self):
        """Test that TxSsi inherits SsiEarnedIncomeDependency from parent Ssi class."""
        from programs.framework.pe_dependencies.member import SsiEarnedIncomeDependency

        self.assertIn(SsiEarnedIncomeDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_ssi_unearned_income_dependency(self):
        """Test that TxSsi inherits SsiUnearnedIncomeDependency from parent Ssi class."""
        from programs.framework.pe_dependencies.member import SsiUnearnedIncomeDependency

        self.assertIn(SsiUnearnedIncomeDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxSsi inherits AgeDependency from parent Ssi class."""
        from programs.framework.pe_dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxSsi.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxSsi has the same pe_outputs as parent Ssi class."""
        # TxSsi should use the same outputs as parent
        self.assertEqual(TxSsi.pe_outputs, Ssi.pe_outputs)
