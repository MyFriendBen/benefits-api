"""
Unit tests for TX member-level PolicyEngine calculator classes.

These tests verify TX-specific calculator logic for member-level programs including:
- TxWic calculator registration and configuration
- TX-specific pe_inputs (TxStateCodeDependency)
- Behavior differences from parent class
"""

from django.test import TestCase

from unittest.mock import Mock, MagicMock

from programs.programs.federal.pe.member import Wic, Ssi, CommoditySupplementalFoodProgram, Medicaid
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies import household, member
from programs.programs.policyengine.calculators.dependencies.household import TxStateCodeDependency
from programs.programs.tx.pe import tx_pe_calculators
from programs.programs.tx.pe.member import TxWic, TxSsi, TxCsfp, TxChip


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

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX WIC is registered in the calculators dictionary."""
        # Verify tx_wic is in the calculators dictionary
        self.assertIn("tx_wic", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_wic"], TxWic)

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
        from programs.programs.policyengine.calculators.dependencies.member import PregnancyDependency

        self.assertIn(PregnancyDependency, TxWic.pe_inputs)
        self.assertEqual(PregnancyDependency.field, "is_pregnant")

    def test_pe_inputs_includes_expected_children_pregnancy_dependency(self):
        """Test that TxWic inherits ExpectedChildrenPregnancyDependency from parent Wic class."""
        from programs.programs.policyengine.calculators.dependencies.member import (
            ExpectedChildrenPregnancyDependency,
        )

        self.assertIn(ExpectedChildrenPregnancyDependency, TxWic.pe_inputs)
        self.assertEqual(ExpectedChildrenPregnancyDependency.field, "current_pregnancies")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxWic inherits AgeDependency from parent Wic class."""
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxWic.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_school_meal_countable_income_dependency(self):
        """Test that TxWic inherits SchoolMealCountableIncomeDependency from parent Wic class."""
        from programs.programs.policyengine.calculators.dependencies.spm import SchoolMealCountableIncomeDependency

        self.assertIn(SchoolMealCountableIncomeDependency, TxWic.pe_inputs)
        self.assertEqual(SchoolMealCountableIncomeDependency.field, "school_meal_countable_income")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxWic has the same pe_outputs as parent Wic class."""
        # TxWic should use the same outputs as parent
        self.assertEqual(TxWic.pe_outputs, Wic.pe_outputs)


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
        self.assertEqual(TxSsi.pe_name, "ssi")
        self.assertIsNotNone(TxSsi.pe_inputs)
        self.assertGreater(len(TxSsi.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX SSI is registered in the calculators dictionary."""
        # Verify tx_ssi is in the calculators dictionary
        self.assertIn("tx_ssi", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_ssi"], TxSsi)

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
        from programs.programs.policyengine.calculators.dependencies.member import (
            SsiCountableResourcesDependency,
        )

        self.assertIn(SsiCountableResourcesDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_ssi_reported_dependency(self):
        """Test that TxSsi inherits SsiReportedDependency from parent Ssi class."""
        from programs.programs.policyengine.calculators.dependencies.member import SsiReportedDependency

        self.assertIn(SsiReportedDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_is_blind_dependency(self):
        """Test that TxSsi inherits IsBlindDependency from parent Ssi class."""
        from programs.programs.policyengine.calculators.dependencies.member import IsBlindDependency

        self.assertIn(IsBlindDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_is_disabled_dependency(self):
        """Test that TxSsi inherits IsDisabledDependency from parent Ssi class."""
        from programs.programs.policyengine.calculators.dependencies.member import IsDisabledDependency

        self.assertIn(IsDisabledDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_ssi_earned_income_dependency(self):
        """Test that TxSsi inherits SsiEarnedIncomeDependency from parent Ssi class."""
        from programs.programs.policyengine.calculators.dependencies.member import SsiEarnedIncomeDependency

        self.assertIn(SsiEarnedIncomeDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_ssi_unearned_income_dependency(self):
        """Test that TxSsi inherits SsiUnearnedIncomeDependency from parent Ssi class."""
        from programs.programs.policyengine.calculators.dependencies.member import SsiUnearnedIncomeDependency

        self.assertIn(SsiUnearnedIncomeDependency, TxSsi.pe_inputs)

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxSsi inherits AgeDependency from parent Ssi class."""
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxSsi.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxSsi has the same pe_outputs as parent Ssi class."""
        # TxSsi should use the same outputs as parent
        self.assertEqual(TxSsi.pe_outputs, Ssi.pe_outputs)


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

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX CSFP is registered in the calculators dictionary."""
        # Verify tx_csfp is in the calculators dictionary
        self.assertIn("tx_csfp", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_csfp"], TxCsfp)

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
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxCsfp.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_school_meal_countable_income_dependency(self):
        """Test that TxCsfp inherits SchoolMealCountableIncomeDependency from parent CommoditySupplementalFoodProgram class."""
        from programs.programs.policyengine.calculators.dependencies.spm import SchoolMealCountableIncomeDependency

        self.assertIn(SchoolMealCountableIncomeDependency, TxCsfp.pe_inputs)
        self.assertEqual(SchoolMealCountableIncomeDependency.field, "school_meal_countable_income")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxCsfp has the same pe_outputs as parent CommoditySupplementalFoodProgram class."""
        # TxCsfp should use the same outputs as parent
        self.assertEqual(TxCsfp.pe_outputs, CommoditySupplementalFoodProgram.pe_outputs)


class TestTxChip(TestCase):
    """Tests for TxChip calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """
        Test that TxChip calculator class exists and inherits from PolicyEngineMembersCalculator.

        This verifies the calculator has been set up in the codebase and follows the
        correct inheritance pattern for member-level calculators.
        """
        # Verify TxChip is a subclass of PolicyEngineMembersCalculator
        self.assertTrue(issubclass(TxChip, PolicyEngineMembersCalculator))

        # Verify it has the expected properties
        self.assertEqual(TxChip.pe_name, "chip")
        self.assertIsNotNone(TxChip.pe_inputs)
        self.assertGreater(len(TxChip.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX CHIP is registered in the calculators dictionary."""
        # Verify tx_chip is in the calculators dictionary
        self.assertIn("tx_chip", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_chip"], TxChip)

    def test_pe_name_is_chip(self):
        """Test that TxChip has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(TxChip.pe_name, "chip")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxChip includes AgeDependency in pe_inputs."""
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxChip.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """Test that TxChip includes PregnancyDependency in pe_inputs."""
        from programs.programs.policyengine.calculators.dependencies.member import PregnancyDependency

        self.assertIn(PregnancyDependency, TxChip.pe_inputs)
        self.assertEqual(PregnancyDependency.field, "is_pregnant")

    def test_pe_inputs_includes_medicaid_inputs(self):
        """
        Test that TxChip includes all Medicaid pe_inputs.

        CHIP eligibility often depends on Medicaid-related factors, so the calculator
        includes all Medicaid dependencies.
        """
        # Verify all Medicaid inputs are present in TxChip
        for medicaid_input in Medicaid.pe_inputs:
            self.assertIn(medicaid_input, TxChip.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX CHIP inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxChip.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_outputs_includes_chip_dependency(self):
        """Test that TxChip has Chip dependency in pe_outputs."""
        from programs.programs.policyengine.calculators.dependencies.member import Chip

        self.assertIn(Chip, TxChip.pe_outputs)

    def test_member_value_returns_pe_value_when_member_has_no_insurance(self):
        """
        Test that member_value returns PolicyEngine value when member has no insurance.

        When a member has no insurance (insurance type 'none'), they should be eligible
        for CHIP and the full PolicyEngine-calculated value should be returned.
        """
        # Create a mock TxChip calculator instance
        calculator = TxChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 200
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member with no insurance
        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=True)  # has_insurance_types(("none",)) returns True

        # Call member_value
        result = calculator.member_value(member)

        # Verify the result is the PolicyEngine value
        self.assertEqual(result, pe_value)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_zero_when_member_has_insurance(self):
        """
        Test that member_value returns 0 when member has insurance.

        If a member has any insurance type other than 'none', they are not eligible
        for CHIP and member_value should return 0.
        """
        # Create a mock TxChip calculator instance
        calculator = TxChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 200
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member with insurance
        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False

        # Call member_value
        result = calculator.member_value(member)

        # Verify the result is 0
        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_calls_get_member_variable_with_member_id(self):
        """
        Test that member_value calls get_member_variable with the correct member ID.

        This verifies that the PolicyEngine value is fetched for the right member.
        """
        # Create a mock TxChip calculator instance
        calculator = TxChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=150)

        # Create a mock member
        member = Mock()
        member.id = 42
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        calculator.member_value(member)

        # Verify get_member_variable was called with the correct member ID
        calculator.get_member_variable.assert_called_once_with(42)

    def test_member_value_insurance_check_happens_before_return(self):
        """
        Test that insurance eligibility check occurs regardless of PolicyEngine value.

        Even if PolicyEngine returns a high value, the insurance check should still
        determine the final eligibility.
        """
        # Create a mock TxChip calculator instance
        calculator = TxChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock high PolicyEngine value
        calculator.get_member_variable = Mock(return_value=500)

        # Create a mock member with insurance (not eligible)
        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 despite high PE value
        self.assertEqual(result, 0)

        # Verify insurance check was performed
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_with_zero_pe_value_and_no_insurance(self):
        """
        Test that member_value returns 0 when PolicyEngine returns 0, even without insurance.

        If PolicyEngine determines no benefit value, it should be returned as-is
        (the member may not be income-eligible even though they have no insurance).
        """
        # Create a mock TxChip calculator instance
        calculator = TxChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock zero PolicyEngine value
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock member with no insurance
        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (PE says not eligible)
        self.assertEqual(result, 0)
