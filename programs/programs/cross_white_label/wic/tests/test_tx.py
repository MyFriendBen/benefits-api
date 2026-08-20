"""TX tests."""

from screener.models import HouseholdMember
from programs.programs.cross_white_label.wic.tx import TxWic
from integrations.clients.policyengine.policy_engine import pe_input
from programs.programs.testing_fixtures.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.programs.cross_white_label.wic.base import Wic
from programs.framework.pe_dependencies import household


class TestTxWicPeInput(TxPeInputTestBase):
    """Tests for TxWic calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxWic pe_inputs dependencies."""
        result = pe_input(self.screen, [TxWic])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]

        # SPM-level dependency: TANF, a WIC income source in its own right
        self.assertIn("tanf", spm_unit)

        # Member-level dependencies
        head_id = str(self.head.id)
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("current_pregnancies", people[head_id])
        self.assertIn("age", people[head_id])
        # WIC's own income sources, which replaced school_meal_countable_income
        self.assertIn("employment_income", people[head_id])
        self.assertIn("child_support_received", people[head_id])

    def test_includes_pe_output_fields(self):
        """Test that pe_input includes TxWic pe_outputs."""
        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]

        for member_id in [str(self.head.id), str(self.spouse.id), str(self.child.id)]:
            self.assertIn("wic", people[member_id])
            self.assertIn("wic_category", people[member_id])

    def test_pregnancy_fields_for_pregnant_member(self):
        """Test that pregnancy fields are populated for pregnant members."""
        pregnant_member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="parent",
            age=28,
            pregnant=True,
        )

        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]
        pregnant_id = str(pregnant_member.id)

        if people[pregnant_id]["is_pregnant"]:
            period_key = list(people[pregnant_id]["is_pregnant"].keys())[0]
            self.assertTrue(people[pregnant_id]["is_pregnant"][period_key])
            self.assertEqual(people[pregnant_id]["current_pregnancies"][period_key], 1)

    def test_handles_infant(self):
        """Test that TxWic correctly handles infants."""
        infant = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=0,
        )

        result = pe_input(self.screen, [TxWic])
        people = result["household"]["people"]
        infant_id = str(infant.id)

        self.assertIn("age", people[infant_id])
        self.assertIn("wic", people[infant_id])


class TestTxWic(TestCase):
    """Tests for TxWic calculator class."""

    def test_exists_and_is_subclass_of_wic(self):
        """
        Test that TxWic calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxWic is a subclass of Wic
        self.assertTrue(issubclass(TxWic, Wic))

        # Verify it has the expected properties
        self.assertEqual(TxWic.pe_name, "wic")
        self.assertIsNotNone(TxWic.pe_inputs)
        self.assertGreater(len(TxWic.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxWic has all expected pe_inputs from parent and TX-specific.

        TxWic should inherit all inputs from parent Wic class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxWic should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxWic.pe_inputs), len(Wic.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxWic.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Wic.pe_inputs:
            self.assertIn(parent_input, TxWic.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX WIC inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxWic.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """Test that TxWic inherits PregnancyDependency from parent Wic class."""
        from programs.framework.pe_dependencies.member import PregnancyDependency

        self.assertIn(PregnancyDependency, TxWic.pe_inputs)
        self.assertEqual(PregnancyDependency.field, "is_pregnant")

    def test_pe_inputs_includes_expected_children_pregnancy_dependency(self):
        """Test that TxWic inherits ExpectedChildrenPregnancyDependency from parent Wic class."""
        from programs.framework.pe_dependencies.member import (
            ExpectedChildrenPregnancyDependency,
        )

        self.assertIn(ExpectedChildrenPregnancyDependency, TxWic.pe_inputs)
        self.assertEqual(ExpectedChildrenPregnancyDependency.field, "current_pregnancies")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxWic inherits AgeDependency from parent Wic class."""
        from programs.framework.pe_dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxWic.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_the_wic_income_bundle(self):
        """TxWic inherits the WIC income sources from the parent Wic class.

        These replaced ``school_meal_countable_income``, which WIC's tree never read: TX WIC
        returned eligible at any reported income until the bundle landed. What the bundle
        covers is pinned in ``federal/pe/tests/test_wic.py``.
        """
        from programs.framework.pe_dependencies import wic_income
        from programs.framework.pe_dependencies.spm import SchoolMealCountableIncomeDependency

        for dep in wic_income:
            self.assertIn(dep, TxWic.pe_inputs)
        self.assertNotIn(SchoolMealCountableIncomeDependency, TxWic.pe_inputs)

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxWic has the same pe_outputs as parent Wic class."""
        # TxWic should use the same outputs as parent
        self.assertEqual(TxWic.pe_outputs, Wic.pe_outputs)
