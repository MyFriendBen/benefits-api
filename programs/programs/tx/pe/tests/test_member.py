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
from programs.programs.tx.pe.member import (
    TxWic,
    TxSsi,
    TxCsfp,
    TxChip,
    TxMedicaidForChildren,
    TxMedicaidForPregnantWomen,
    TxMedicaidForParentsAndCaretakers,
    TxHarrisCountyRides,
    TxEmergencyMedicaid,
    TxDart,
    TxFpp,
)


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


class TestTxMedicaidForChildren(TestCase):
    """Tests for TxMedicaidForChildren calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxMedicaidForChildren calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxMedicaidForChildren is a subclass of Medicaid
        self.assertTrue(issubclass(TxMedicaidForChildren, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxMedicaidForChildren.pe_name, "medicaid")
        self.assertIsNotNone(TxMedicaidForChildren.pe_inputs)
        self.assertGreater(len(TxMedicaidForChildren.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX Medicaid for Children is registered in the calculators dictionary."""
        # Verify tx_medicaid_for_children is in the calculators dictionary
        self.assertIn("tx_medicaid_for_children", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_medicaid_for_children"], TxMedicaidForChildren)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxMedicaidForChildren has all expected pe_inputs from parent and TX-specific.

        TxMedicaidForChildren should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxMedicaidForChildren should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxMedicaidForChildren.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxMedicaidForChildren.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxMedicaidForChildren.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Medicaid inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxMedicaidForChildren.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxMedicaidForChildren has the same pe_outputs as parent Medicaid class."""
        # TxMedicaidForChildren should use the same outputs as parent
        self.assertEqual(TxMedicaidForChildren.pe_outputs, Medicaid.pe_outputs)

    def test_member_value_returns_zero_for_adults_age_19_or_older(self):
        """
        Test that member_value returns 0 for members aged 19 or older.

        TX Medicaid for Children is only for children under 19.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the parent's member_value method
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member aged 19
        member = Mock()
        member.id = 1
        member.age = 19
        member.has_insurance_types = Mock(return_value=True)
        member.has_disability = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (too old)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_for_children_with_insurance(self):
        """
        Test that member_value returns 0 for children who have other insurance.

        TX Medicaid for Children requires that children do not have other health insurance.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member under 19 with insurance
        member = Mock()
        member.id = 1
        member.age = 10
        member.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False
        member.has_disability = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (has insurance)
        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_pe_value_for_eligible_children(self):
        """
        Test that member_value returns PolicyEngine value for eligible children.

        When a child is under 19 and has no insurance, the PolicyEngine-calculated
        Medicaid value should be returned directly.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 250
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member under 19 without insurance
        member = Mock()
        member.id = 1
        member.age = 12
        member.has_insurance_types = Mock(return_value=True)  # has_insurance_types(("none",)) returns True

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value directly
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_age_boundary_18_is_eligible(self):
        """
        Test that 18-year-olds are eligible for TX Medicaid for Children.

        The program covers children 18 and under, so 18 should be eligible.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 300
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member aged 18 without insurance
        member = Mock()
        member.id = 1
        member.age = 18
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value (18 is eligible)
        self.assertEqual(result, pe_value)

    def test_member_value_checks_age_before_insurance(self):
        """
        Test that age check happens before insurance check for efficiency.

        If a member is too old, we shouldn't need to check their insurance status.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock member aged 25
        member = Mock()
        member.id = 1
        member.age = 25
        member.has_insurance_types = Mock()  # Should not be called

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0
        self.assertEqual(result, 0)

        # Insurance check should not be called since age check fails first
        member.has_insurance_types.assert_not_called()

    def test_member_value_with_infant(self):
        """
        Test that member_value works correctly for infants (age 0).

        Infants should be eligible if they have no other insurance.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 400
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock infant without insurance
        member = Mock()
        member.id = 1
        member.age = 0
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value (infant is eligible)
        self.assertEqual(result, pe_value)


class TestTxMedicaidForPregnantWomen(TestCase):
    """Tests for TxMedicaidForPregnantWomen calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxMedicaidForPregnantWomen calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxMedicaidForPregnantWomen is a subclass of Medicaid
        self.assertTrue(issubclass(TxMedicaidForPregnantWomen, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxMedicaidForPregnantWomen.pe_name, "medicaid")
        self.assertIsNotNone(TxMedicaidForPregnantWomen.pe_inputs)
        self.assertGreater(len(TxMedicaidForPregnantWomen.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX Medicaid for Pregnant Women is registered in the calculators dictionary."""
        # Verify tx_medicaid_for_pregnant_women is in the calculators dictionary
        self.assertIn("tx_medicaid_for_pregnant_women", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_medicaid_for_pregnant_women"], TxMedicaidForPregnantWomen)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxMedicaidForPregnantWomen has all expected pe_inputs from parent and TX-specific.

        TxMedicaidForPregnantWomen should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxMedicaidForPregnantWomen should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxMedicaidForPregnantWomen.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxMedicaidForPregnantWomen.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxMedicaidForPregnantWomen.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Medicaid inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxMedicaidForPregnantWomen.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxMedicaidForPregnantWomen has the same pe_outputs as parent Medicaid class."""
        # TxMedicaidForPregnantWomen should use the same outputs as parent
        self.assertEqual(TxMedicaidForPregnantWomen.pe_outputs, Medicaid.pe_outputs)

    def test_member_value_returns_zero_for_non_pregnant_members(self):
        """
        Test that member_value returns 0 for members who are not pregnant.

        TX Medicaid for Pregnant Women is only for pregnant individuals.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the parent's member_value method
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member who is not pregnant
        member = Mock()
        member.id = 1
        member.pregnant = False
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (not pregnant)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_for_pregnant_members_with_insurance(self):
        """
        Test that member_value returns 0 for pregnant members who have other insurance.

        TX Medicaid for Pregnant Women requires that pregnant persons do not have other health insurance.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock pregnant member with insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (has insurance)
        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_pe_value_for_eligible_pregnant_women(self):
        """
        Test that member_value returns PolicyEngine value for eligible pregnant women.

        When a member is pregnant and has no insurance, the PolicyEngine-calculated
        Medicaid value should be returned directly.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 350
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)  # has_insurance_types(("none",)) returns True

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value directly
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_checks_pregnancy_before_insurance(self):
        """
        Test that pregnancy check happens before insurance check for efficiency.

        If a member is not pregnant, we shouldn't need to check their insurance status.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock non-pregnant member
        member = Mock()
        member.id = 1
        member.pregnant = False
        member.has_insurance_types = Mock()  # Should not be called

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0
        self.assertEqual(result, 0)

        # Insurance check should not be called since pregnancy check fails first
        member.has_insurance_types.assert_not_called()

    def test_member_value_with_zero_pe_value_and_eligible_pregnant_woman(self):
        """
        Test that member_value returns 0 when PolicyEngine returns 0, even for eligible pregnant women.

        If PolicyEngine determines no benefit value, it should be returned as-is
        (the member may not be income-eligible even though they are pregnant and have no insurance).
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock zero PolicyEngine value
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (PE says not eligible based on income)
        self.assertEqual(result, 0)

    def test_member_value_with_high_pe_value_but_has_insurance(self):
        """
        Test that insurance eligibility check occurs regardless of PolicyEngine value.

        Even if PolicyEngine returns a high value, the insurance check should still
        determine the final eligibility.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock high PolicyEngine value
        calculator.get_member_variable = Mock(return_value=500)

        # Create a mock pregnant member with insurance (not eligible)
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 despite high PE value
        self.assertEqual(result, 0)

        # Verify insurance check was performed
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_calls_get_member_variable_with_member_id(self):
        """
        Test that member_value calls get_member_variable with the correct member ID.

        This verifies that the PolicyEngine value is fetched for the right member.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=200)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 99
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        calculator.member_value(member)

        # Verify get_member_variable was called with the correct member ID
        calculator.get_member_variable.assert_called_once_with(99)


class TestTxMedicaidForParentsAndCaretakers(TestCase):
    """Tests for TxMedicaidForParentsAndCaretakers calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxMedicaidForParentsAndCaretakers calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxMedicaidForParentsAndCaretakers is a subclass of Medicaid
        self.assertTrue(issubclass(TxMedicaidForParentsAndCaretakers, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxMedicaidForParentsAndCaretakers.pe_name, "medicaid")
        self.assertIsNotNone(TxMedicaidForParentsAndCaretakers.pe_inputs)
        self.assertGreater(len(TxMedicaidForParentsAndCaretakers.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX Medicaid for Parents and Caretakers is registered in the calculators dictionary."""
        # Verify tx_medicaid_for_parents_and_caretakers is in the calculators dictionary
        self.assertIn("tx_medicaid_for_parents_and_caretakers", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_medicaid_for_parents_and_caretakers"], TxMedicaidForParentsAndCaretakers)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxMedicaidForParentsAndCaretakers has all expected pe_inputs from parent and TX-specific.

        TxMedicaidForParentsAndCaretakers should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxMedicaidForParentsAndCaretakers should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxMedicaidForParentsAndCaretakers.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxMedicaidForParentsAndCaretakers.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxMedicaidForParentsAndCaretakers.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Medicaid for Parents inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxMedicaidForParentsAndCaretakers.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxMedicaidForParentsAndCaretakers has the same pe_outputs as parent Medicaid class."""
        # TxMedicaidForParentsAndCaretakers should use the same outputs as parent
        self.assertEqual(TxMedicaidForParentsAndCaretakers.pe_outputs, Medicaid.pe_outputs)

    def test_caretaker_relationships_defined(self):
        """Test that caretaker relationships are properly defined."""
        expected_relationships = [
            "headOfHousehold",
            "spouse",
            "domesticPartner",
            "parent",
            "stepParent",
            "grandParent",
            "sisterOrBrother",
            "stepSisterOrBrother",
            "relatedOther",
        ]

        self.assertEqual(TxMedicaidForParentsAndCaretakers.caretaker_relationships, expected_relationships)

    def test_member_value_returns_zero_for_children_under_19(self):
        """
        Test that member_value returns 0 for members under 19.

        TX Medicaid for Parents and Caretakers is for adults 19 and older.
        """
        # Create a mock calculator instance
        calculator = TxMedicaidForParentsAndCaretakers(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)

        # Create a mock member aged 18
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 18
        member_obj.has_insurance_types = Mock(return_value=True)
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (too young)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_for_adults_with_insurance(self):
        """
        Test that member_value returns 0 for adults who have other health insurance.

        TX Medicaid for Parents and Caretakers requires that adults do not have other insurance.
        """
        # Create a mock calculator instance
        calculator = TxMedicaidForParentsAndCaretakers(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)

        # Create a mock adult with insurance
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (has insurance)
        self.assertEqual(result, 0)
        member_obj.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_zero_for_non_caretaker_relationship(self):
        """
        Test that member_value returns 0 for adults with non-caretaker relationships.

        Only certain relationships qualify as caretakers (headOfHousehold, spouse, domesticPartner,
        parent, stepParent, grandParent, sisterOrBrother, stepSisterOrBrother, relatedOther).
        """
        # Create a mock calculator instance with screen
        mock_screen = Mock()
        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)

        # Create a mock adult with a non-qualifying relationship (e.g., "other")
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=True)  # No insurance
        member_obj.relationship = "other"  # Not a qualifying relationship

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (not a qualifying caretaker relationship)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_when_no_child_with_medicaid(self):
        """
        Test that member_value returns 0 when household has no child under 19 with Medicaid.

        A qualifying child must be in the household for caretaker eligibility.
        """
        # Create a mock screen with no children
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = []  # No children in household
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)

        # Create a mock adult caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=True)  # No insurance
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (no child with Medicaid in household)
        self.assertEqual(result, 0)

    def test_member_value_returns_pe_value_for_eligible_caretaker(self):
        """
        Test that member_value returns PolicyEngine value for eligible caretakers.

        When an adult is 19+, has no insurance, has a qualifying relationship,
        and household has a child with Medicaid, the PE value should be returned.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 10
        mock_child.has_benefit = Mock(return_value=True)  # Child has Medicaid

        # Create a mock screen with the child
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        pe_value = 300
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock eligible adult caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=True)  # No insurance
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the PolicyEngine value
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_with(1)

    def test_member_value_eligible_with_child_qualifying_for_medicaid(self):
        """
        Test that caretaker is eligible when child qualifies for Medicaid (PE value > 0).

        Even if child doesn't currently have Medicaid, if they qualify (PE value > 0),
        the caretaker should be eligible.
        """
        # Create a mock child who qualifies for Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 10
        mock_child.has_benefit = Mock(return_value=False)  # Child doesn't have Medicaid yet

        # Create a mock screen with the child
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine values - child qualifies (> 0), adult also qualifies
        calculator.get_member_dependency_value = Mock(return_value=250)  # Child qualifies for Medicaid
        calculator.get_member_variable = Mock(return_value=300)  # Adult's value

        # Create a mock eligible adult caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=True)  # No insurance
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the adult's PolicyEngine value
        self.assertEqual(result, 300)

    def test_member_value_age_boundary_19_is_eligible(self):
        """
        Test that 19-year-olds are eligible (minimum age for the program).

        The program covers adults 19 and older.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 5
        mock_child.has_benefit = Mock(return_value=True)

        # Create a mock screen
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        pe_value = 350
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member aged 19
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 19
        member_obj.has_insurance_types = Mock(return_value=True)
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the PolicyEngine value (19 is eligible)
        self.assertEqual(result, pe_value)

    def test_member_value_checks_age_before_other_conditions(self):
        """
        Test that age check happens first for efficiency.

        If a member is under 19, we shouldn't need to check other conditions.
        """
        # Create a mock calculator instance
        calculator = TxMedicaidForParentsAndCaretakers(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock member aged 17
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 17
        member_obj.has_insurance_types = Mock()  # Should not be called
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0
        self.assertEqual(result, 0)

        # Insurance check should not be called since age check fails first
        member_obj.has_insurance_types.assert_not_called()

    def test_member_value_with_sibling_relationship(self):
        """
        Test that sibling relationship qualifies as a caretaker.

        From the requirements, siblings are valid caretakers.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 10
        mock_child.has_benefit = Mock(return_value=True)

        # Create a mock screen
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        pe_value = 280
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock adult sibling caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 25
        member_obj.has_insurance_types = Mock(return_value=True)
        member_obj.relationship = "sisterOrBrother"  # Sibling relationship

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the PolicyEngine value (sibling is eligible caretaker)
        self.assertEqual(result, pe_value)

    def test_member_value_with_grandparent_relationship(self):
        """
        Test that grandparent relationship qualifies as a caretaker.

        From the requirements, grandparents are valid caretakers.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 8
        mock_child.has_benefit = Mock(return_value=True)

        # Create a mock screen
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        pe_value = 320
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock grandparent caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 65
        member_obj.has_insurance_types = Mock(return_value=True)
        member_obj.relationship = "grandParent"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the PolicyEngine value (grandparent is eligible caretaker)
        self.assertEqual(result, pe_value)

    def test_has_child_with_medicaid_returns_false_for_adult_only_household(self):
        """
        Test _has_child_with_medicaid returns False when household has no children under 19.
        """
        # Create mock adult members only
        mock_adult = Mock()
        mock_adult.id = 2
        mock_adult.age = 35

        # Create a mock screen with adult only
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_adult]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Call _has_child_with_medicaid
        result = calculator._has_child_with_medicaid()

        # Should return False (no children under 19)
        self.assertFalse(result)

    def test_has_child_with_medicaid_returns_true_for_child_with_benefit(self):
        """
        Test _has_child_with_medicaid returns True when child has Medicaid benefit.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 10
        mock_child.has_benefit = Mock(return_value=True)

        # Create a mock screen with the child
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Call _has_child_with_medicaid
        result = calculator._has_child_with_medicaid()

        # Should return True
        self.assertTrue(result)
        mock_child.has_benefit.assert_called_once_with("medicaid")

    def test_has_child_with_medicaid_returns_true_for_child_qualifying_via_pe(self):
        """
        Test _has_child_with_medicaid returns True when child qualifies via PolicyEngine value.
        """
        # Create a mock child who qualifies for Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 12
        mock_child.has_benefit = Mock(return_value=False)  # Doesn't have it yet

        # Create a mock screen with the child
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value > 0 (child qualifies)
        calculator.get_member_dependency_value = Mock(return_value=200)

        # Call _has_child_with_medicaid
        result = calculator._has_child_with_medicaid()

        # Should return True
        self.assertTrue(result)
        calculator.get_member_dependency_value.assert_called_once()


class TestTxHarrisCountyRides(TestCase):
    """Tests for TxHarrisCountyRides calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """
        Test that TxHarrisCountyRides calculator class exists and inherits from PolicyEngineMembersCalculator.

        This verifies the calculator has been set up in the codebase and follows the
        correct inheritance pattern for member-level calculators.
        """
        # Verify TxHarrisCountyRides is a subclass of PolicyEngineMembersCalculator
        self.assertTrue(issubclass(TxHarrisCountyRides, PolicyEngineMembersCalculator))

        # Verify it has the expected properties
        self.assertEqual(TxHarrisCountyRides.pe_name, "tx_harris_rides_eligible")
        self.assertIsNotNone(TxHarrisCountyRides.pe_inputs)
        self.assertGreater(len(TxHarrisCountyRides.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX Harris County RIDES is registered in the calculators dictionary."""
        # Verify tx_harris_rides is in the calculators dictionary
        self.assertIn("tx_harris_rides", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_harris_rides"], TxHarrisCountyRides)

    def test_pe_name_is_tx_harris_rides_eligible(self):
        """Test that TxHarrisCountyRides has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(TxHarrisCountyRides.pe_name, "tx_harris_rides_eligible")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxHarrisCountyRides includes AgeDependency in pe_inputs."""
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxHarrisCountyRides.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_is_disabled_dependency(self):
        """Test that TxHarrisCountyRides includes IsDisabledDependency in pe_inputs."""
        from programs.programs.policyengine.calculators.dependencies.member import IsDisabledDependency

        self.assertIn(IsDisabledDependency, TxHarrisCountyRides.pe_inputs)
        self.assertEqual(IsDisabledDependency.field, "is_disabled")

    def test_pe_inputs_includes_is_blind_dependency(self):
        """Test that TxHarrisCountyRides includes IsBlindDependency in pe_inputs."""
        from programs.programs.policyengine.calculators.dependencies.member import IsBlindDependency

        self.assertIn(IsBlindDependency, TxHarrisCountyRides.pe_inputs)
        self.assertEqual(IsBlindDependency.field, "is_blind")

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Harris County RIDES inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxHarrisCountyRides.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_county_dependency(self):
        """Test that TxHarrisCountyRides has county dependency configured."""
        self.assertIn("county", TxHarrisCountyRides.dependencies)

    def test_member_value_returns_one_when_eligible(self):
        """
        Test that member_value returns 1 when PolicyEngine indicates eligibility.

        When PolicyEngine returns True for tx_harris_rides_eligible (which includes
        the county check), the calculator should return 1 to indicate eligibility.
        """
        # Create a mock screen
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=False)

        # Create a mock TxHarrisCountyRides calculator instance
        calculator = TxHarrisCountyRides(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return True (eligible)
        calculator.get_member_variable = Mock(return_value=True)

        # Create a mock member
        member_obj = Mock()
        member_obj.id = 1

        # Call member_value
        result = calculator.member_value(member_obj)

        # Verify the result is 1
        self.assertEqual(result, 1)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_returns_zero_when_not_eligible(self):
        """
        Test that member_value returns 0 when PolicyEngine indicates ineligibility.

        When PolicyEngine returns False for tx_harris_rides_eligible (which includes
        county check), the calculator should return 0 to indicate the member is not eligible.
        """
        # Create a mock screen
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=False)

        # Create a mock TxHarrisCountyRides calculator instance
        calculator = TxHarrisCountyRides(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return False (not eligible)
        calculator.get_member_variable = Mock(return_value=False)

        # Create a mock member
        member_obj = Mock()
        member_obj.id = 2

        # Call member_value
        result = calculator.member_value(member_obj)

        # Verify the result is 0
        self.assertEqual(result, 0)
        calculator.get_member_variable.assert_called_once_with(2)

    def test_member_value_calls_get_member_variable_with_member_id(self):
        """
        Test that member_value calls get_member_variable with the correct member ID.

        This verifies that the PolicyEngine eligibility value is fetched for the right member.
        """
        # Create a mock screen
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=False)

        # Create a mock TxHarrisCountyRides calculator instance
        calculator = TxHarrisCountyRides(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=True)

        # Create a mock member with specific ID
        member_obj = Mock()
        member_obj.id = 42

        # Call member_value
        calculator.member_value(member_obj)

        # Verify get_member_variable was called with the correct member ID
        calculator.get_member_variable.assert_called_once_with(42)

    def test_member_value_returns_zero_for_falsy_pe_value(self):
        """
        Test that member_value returns 0 for any falsy PolicyEngine value.

        This covers cases where PolicyEngine might return 0, None, or empty values.
        """
        # Create a mock screen
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=False)

        # Create a mock TxHarrisCountyRides calculator instance
        calculator = TxHarrisCountyRides(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        member_obj = Mock()
        member_obj.id = 1

        # Test with 0
        calculator.get_member_variable = Mock(return_value=0)
        self.assertEqual(calculator.member_value(member_obj), 0)

        # Test with None
        calculator.get_member_variable = Mock(return_value=None)
        self.assertEqual(calculator.member_value(member_obj), 0)

        # Test with empty string
        calculator.get_member_variable = Mock(return_value="")
        self.assertEqual(calculator.member_value(member_obj), 0)

    def test_member_value_returns_one_for_truthy_pe_value(self):
        """
        Test that member_value returns 1 for any truthy PolicyEngine value.

        This covers cases where PolicyEngine might return 1, True, or other truthy values.
        """
        # Create a mock screen
        mock_screen = Mock()
        mock_screen.has_benefit = Mock(return_value=False)

        # Create a mock TxHarrisCountyRides calculator instance
        calculator = TxHarrisCountyRides(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        member_obj = Mock()
        member_obj.id = 1

        # Test with 1
        calculator.get_member_variable = Mock(return_value=1)
        self.assertEqual(calculator.member_value(member_obj), 1)

        # Test with True
        calculator.get_member_variable = Mock(return_value=True)
        self.assertEqual(calculator.member_value(member_obj), 1)


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

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX Emergency Medicaid is registered in the calculators dictionary."""
        # Verify tx_emergency_medicaid is in the calculators dictionary
        self.assertIn("tx_emergency_medicaid", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_emergency_medicaid"], TxEmergencyMedicaid)

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


class TestTxDart(TestCase):
    """Tests for TxDart calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """
        Test that TxDart calculator class exists and inherits from PolicyEngineMembersCalculator.

        This verifies the calculator has been set up in the codebase and follows the
        correct inheritance pattern for member-level calculators.
        """
        # Verify TxDart is a subclass of PolicyEngineMembersCalculator
        self.assertTrue(issubclass(TxDart, PolicyEngineMembersCalculator))

        # Verify it has the expected properties
        self.assertEqual(TxDart.pe_name, "tx_dart_benefit_person")
        self.assertIsNotNone(TxDart.pe_inputs)
        self.assertGreater(len(TxDart.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX DART is registered in the calculators dictionary."""
        # Verify tx_dart is in the calculators dictionary
        self.assertIn("tx_dart", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_dart"], TxDart)

    def test_pe_name_is_tx_dart_benefit_person(self):
        """Test that TxDart has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(TxDart.pe_name, "tx_dart_benefit_person")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxDart includes AgeDependency in pe_inputs."""
        self.assertIn(member.AgeDependency, TxDart.pe_inputs)
        self.assertEqual(member.AgeDependency.field, "age")

    def test_pe_inputs_includes_is_disabled_dependency(self):
        """Test that TxDart includes IsDisabledDependency in pe_inputs."""
        self.assertIn(member.IsDisabledDependency, TxDart.pe_inputs)
        self.assertEqual(member.IsDisabledDependency.field, "is_disabled")

    def test_pe_inputs_includes_is_veteran_dependency(self):
        """Test that TxDart includes IsVeteranDependency in pe_inputs."""
        self.assertIn(member.IsVeteranDependency, TxDart.pe_inputs)
        self.assertEqual(member.IsVeteranDependency.field, "is_veteran")

    def test_pe_inputs_includes_full_time_college_student_dependency(self):
        """Test that TxDart includes FullTimeCollegeStudentDependency in pe_inputs."""
        self.assertIn(member.FullTimeCollegeStudentDependency, TxDart.pe_inputs)
        self.assertEqual(member.FullTimeCollegeStudentDependency.field, "is_full_time_college_student")

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX DART inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxDart.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_medicaid_inputs(self):
        """
        Test that TxDart includes all Medicaid pe_inputs.

        DART eligibility can be based on enrollment in Medicaid and other
        assistance programs, so the calculator includes Medicaid dependencies.
        """
        # Verify all Medicaid inputs are present in TxDart
        for medicaid_input in Medicaid.pe_inputs:
            self.assertIn(medicaid_input, TxDart.pe_inputs)

    def test_pe_outputs_includes_tx_dart_benefit_person_dependency(self):
        """Test that TxDart has TxDartBenefitPerson dependency in pe_outputs."""
        self.assertIn(member.TxDartBenefitPerson, TxDart.pe_outputs)

    def test_member_value_returns_pe_value_directly(self):
        """
        Test that member_value returns PolicyEngine value directly.

        DART eligibility is fully determined by PolicyEngine, so we return
        the calculated value without additional business logic.
        """
        # Create a mock TxDart calculator instance
        calculator = TxDart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 756  # Reduced fare annual benefit
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member
        mock_member = Mock()
        mock_member.id = 1

        # Call member_value
        result = calculator.member_value(mock_member)

        # Verify the result is the PolicyEngine value
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_returns_free_ride_value(self):
        """
        Test that member_value can return the free ride benefit value.

        Children under 5 are eligible for free rides ($1,512/year).
        """
        # Create a mock TxDart calculator instance
        calculator = TxDart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return free ride value
        pe_value = 1512  # Free ride annual benefit
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member (child under 5)
        mock_member = Mock()
        mock_member.id = 2

        # Call member_value
        result = calculator.member_value(mock_member)

        # Verify the result is the free ride value
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(2)

    def test_member_value_returns_zero_for_ineligible_member(self):
        """
        Test that member_value returns 0 for ineligible members.

        If PolicyEngine determines a member is ineligible, it returns 0.
        """
        # Create a mock TxDart calculator instance
        calculator = TxDart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return 0
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock member who doesn't qualify
        mock_member = Mock()
        mock_member.id = 3

        # Call member_value
        result = calculator.member_value(mock_member)

        # Verify the result is 0
        self.assertEqual(result, 0)
        calculator.get_member_variable.assert_called_once_with(3)

    def test_member_value_calls_get_member_variable_with_correct_member_id(self):
        """
        Test that member_value calls get_member_variable with the correct member ID.

        This verifies that the PolicyEngine value is fetched for the right member.
        """
        # Create a mock TxDart calculator instance
        calculator = TxDart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=756)

        # Create a mock member with a specific ID
        mock_member = Mock()
        mock_member.id = 42

        # Call member_value
        calculator.member_value(mock_member)

        # Verify get_member_variable was called with the correct member ID
        calculator.get_member_variable.assert_called_once_with(42)


class TestTxFpp(TestCase):
    """Tests for TxFpp (Texas Family Planning Program) calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """
        Test that TxFpp calculator class exists and inherits from PolicyEngineMembersCalculator.

        This verifies the calculator has been set up in the codebase and follows the
        correct inheritance pattern for member-level calculators.
        """
        # Verify TxFpp is a subclass of PolicyEngineMembersCalculator
        self.assertTrue(issubclass(TxFpp, PolicyEngineMembersCalculator))

        # Verify it has the expected properties
        self.assertEqual(TxFpp.pe_name, "tx_fpp_benefit")
        self.assertIsNotNone(TxFpp.pe_inputs)
        self.assertGreater(len(TxFpp.pe_inputs), 0)

    def test_is_registered_in_tx_pe_calculators(self):
        """Test that TX FPP is registered in the calculators dictionary."""
        # Verify tx_fpp is in the calculators dictionary
        self.assertIn("tx_fpp", tx_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(tx_pe_calculators["tx_fpp"], TxFpp)

    def test_pe_name_is_tx_fpp_benefit(self):
        """Test that TxFpp has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(TxFpp.pe_name, "tx_fpp_benefit")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxFpp includes AgeDependency in pe_inputs."""
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxFpp.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX FPP inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxFpp.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_irs_gross_income_dependencies(self):
        """
        Test that TxFpp includes all irs_gross_income dependencies.

        FPP eligibility requires income at or below 250% FPL. PolicyEngine's
        tx_fpp_income_eligible formula uses spm_unit_net_income which derives
        from market_income, so we need to provide income inputs.
        """
        from programs.programs.policyengine.calculators.dependencies.member import (
            EmploymentIncomeDependency,
            SelfEmploymentIncomeDependency,
            RentalIncomeDependency,
            PensionIncomeDependency,
            SocialSecurityIncomeDependency,
        )

        # Verify all irs_gross_income dependencies are present
        self.assertIn(EmploymentIncomeDependency, TxFpp.pe_inputs)
        self.assertIn(SelfEmploymentIncomeDependency, TxFpp.pe_inputs)
        self.assertIn(RentalIncomeDependency, TxFpp.pe_inputs)
        self.assertIn(PensionIncomeDependency, TxFpp.pe_inputs)
        self.assertIn(SocialSecurityIncomeDependency, TxFpp.pe_inputs)

    def test_pe_outputs_includes_tx_fpp_dependency(self):
        """Test that TxFpp has TxFpp dependency in pe_outputs."""
        from programs.programs.policyengine.calculators.dependencies.member import TxFpp as TxFppDependency

        self.assertIn(TxFppDependency, TxFpp.pe_outputs)
        self.assertEqual(TxFppDependency.field, "tx_fpp_benefit")

    def test_member_value_returns_pe_value_when_member_has_no_insurance(self):
        """
        Test that member_value returns PolicyEngine value when member has no insurance.

        When a member has no insurance (insurance type 'none'), they should be eligible
        for FPP and the full PolicyEngine-calculated value should be returned.
        """
        # Create a mock TxFpp calculator instance
        calculator = TxFpp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 431
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member with no insurance
        member_obj = Mock()
        member_obj.id = 1
        member_obj.has_insurance_types = Mock(return_value=True)  # has_insurance_types(("none",)) returns True

        # Call member_value
        result = calculator.member_value(member_obj)

        # Verify the result is the PolicyEngine value
        self.assertEqual(result, pe_value)
        member_obj.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_zero_when_member_has_insurance(self):
        """
        Test that member_value returns 0 when member has insurance.

        If a member has any insurance type other than 'none', they are not eligible
        for FPP (which is designed for those without Medicaid coverage) and
        member_value should return 0.
        """
        # Create a mock TxFpp calculator instance
        calculator = TxFpp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 431
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member with insurance
        member_obj = Mock()
        member_obj.id = 1
        member_obj.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False

        # Call member_value
        result = calculator.member_value(member_obj)

        # Verify the result is 0
        self.assertEqual(result, 0)
        member_obj.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_calls_get_member_variable_with_member_id(self):
        """
        Test that member_value calls get_member_variable with the correct member ID.

        This verifies that the PolicyEngine value is fetched for the right member.
        """
        # Create a mock TxFpp calculator instance
        calculator = TxFpp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=431)

        # Create a mock member
        member_obj = Mock()
        member_obj.id = 42
        member_obj.has_insurance_types = Mock(return_value=True)

        # Call member_value
        calculator.member_value(member_obj)

        # Verify get_member_variable was called with the correct member ID
        calculator.get_member_variable.assert_called_once_with(42)

    def test_member_value_insurance_check_happens_before_pe_lookup(self):
        """
        Test that insurance eligibility check occurs before PolicyEngine lookup.

        If a member has insurance, we should return 0 without needing to look up
        the PolicyEngine value.
        """
        # Create a mock TxFpp calculator instance
        calculator = TxFpp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock get_member_variable - should NOT be called
        calculator.get_member_variable = Mock(return_value=500)

        # Create a mock member with insurance (not eligible)
        member_obj = Mock()
        member_obj.id = 1
        member_obj.has_insurance_types = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0
        self.assertEqual(result, 0)

        # Verify insurance check was performed
        member_obj.has_insurance_types.assert_called_once_with(("none",))

        # Verify get_member_variable was NOT called (optimization)
        calculator.get_member_variable.assert_not_called()

    def test_member_value_with_zero_pe_value_and_no_insurance(self):
        """
        Test that member_value returns 0 when PolicyEngine returns 0, even without insurance.

        If PolicyEngine determines no benefit value (e.g., due to age or income ineligibility),
        it should be returned as-is.
        """
        # Create a mock TxFpp calculator instance
        calculator = TxFpp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock zero PolicyEngine value
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock member with no insurance
        member_obj = Mock()
        member_obj.id = 1
        member_obj.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (PE says not eligible - likely due to age/income)
        self.assertEqual(result, 0)

    def test_member_value_with_high_pe_value_but_has_insurance(self):
        """
        Test that insurance eligibility check occurs regardless of PolicyEngine value.

        Even if PolicyEngine returns a high value, the insurance check should still
        determine the final eligibility.
        """
        # Create a mock TxFpp calculator instance
        calculator = TxFpp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock high PolicyEngine value
        calculator.get_member_variable = Mock(return_value=500)

        # Create a mock member with insurance (not eligible)
        member_obj = Mock()
        member_obj.id = 1
        member_obj.has_insurance_types = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 despite high PE value
        self.assertEqual(result, 0)

        # Verify insurance check was performed
        member_obj.has_insurance_types.assert_called_once_with(("none",))
