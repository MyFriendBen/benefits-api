"""TX tests."""

from screener.models import HouseholdMember
from programs.programs.cross_white_label.csfp.tx import TxCsfp
from integrations.clients.policyengine.policy_engine import pe_input
from programs.programs.testing.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household


class TestTxCsfpPeInput(TxPeInputTestBase):
    """Tests for TxCsfp calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxCsfp pe_inputs dependencies."""
        result = pe_input(self.screen, [TxCsfp])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        self.assertIn("school_meal_countable_income", spm_unit)
        self.assertIn("age", people[head_id])

    def test_includes_pe_output_fields(self):
        """Test that pe_input includes TxCsfp pe_outputs."""
        result = pe_input(self.screen, [TxCsfp])
        people = result["household"]["people"]

        for member_id in [str(self.head.id), str(self.spouse.id), str(self.child.id)]:
            self.assertIn("commodity_supplemental_food_program", people[member_id])

    def test_handles_senior_member(self):
        """Test that TxCsfp correctly handles senior members (60+)."""
        senior = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="parent",
            age=65,
        )

        result = pe_input(self.screen, [TxCsfp])
        people = result["household"]["people"]
        senior_id = str(senior.id)

        if people[senior_id]["age"]:
            period_key = list(people[senior_id]["age"].keys())[0]
            self.assertEqual(people[senior_id]["age"][period_key], 65)


class TestTxCsfp(TestCase):
    """Tests for TxCsfp calculator class."""

    def test_exists_and_is_subclass_of_csfp(self):
        """
        Test that TxCsfp calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxCsfp is a subclass of CommoditySupplementalFoodProgram
        self.assertTrue(issubclass(TxCsfp, CommoditySupplementalFoodProgram))

        # Verify it has the expected properties
        self.assertEqual(TxCsfp.pe_name, "commodity_supplemental_food_program")
        self.assertIsNotNone(TxCsfp.pe_inputs)
        self.assertGreater(len(TxCsfp.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxCsfp has all expected pe_inputs from parent and TX-specific.

        TxCsfp should inherit all inputs from parent CommoditySupplementalFoodProgram class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxCsfp should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxCsfp.pe_inputs), len(CommoditySupplementalFoodProgram.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxCsfp.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in CommoditySupplementalFoodProgram.pe_inputs:
            self.assertIn(parent_input, TxCsfp.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX CSFP inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxCsfp.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxCsfp inherits AgeDependency from parent CommoditySupplementalFoodProgram class."""
        from programs.framework.pe_dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxCsfp.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_school_meal_countable_income_dependency(self):
        """Test that TxCsfp inherits SchoolMealCountableIncomeDependency from parent CommoditySupplementalFoodProgram class."""
        from programs.framework.pe_dependencies.spm import SchoolMealCountableIncomeDependency

        self.assertIn(SchoolMealCountableIncomeDependency, TxCsfp.pe_inputs)
        self.assertEqual(SchoolMealCountableIncomeDependency.field, "school_meal_countable_income")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxCsfp has the same pe_outputs as parent CommoditySupplementalFoodProgram class."""
        # TxCsfp should use the same outputs as parent
        self.assertEqual(TxCsfp.pe_outputs, CommoditySupplementalFoodProgram.pe_outputs)
