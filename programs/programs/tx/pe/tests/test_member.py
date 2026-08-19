"""
Unit tests for TX member-level PolicyEngine calculator classes.

These tests verify TX-specific calculator logic for member-level programs including:
- TxWic calculator registration and configuration
- TX-specific pe_inputs (TxStateCodeDependency)
- Behavior differences from parent class
"""

from django.test import TestCase

from unittest.mock import Mock, MagicMock

from programs.programs.federal.pe.member import Wic, Ssi, CommoditySupplementalFoodProgram, HeadStart, EarlyHeadStart
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import household, member
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.programs.tx.pe.member import (
    TxWic,
    TxSsi,
    TxCsfp,
    TxChip,
    TxHarrisCountyRides,
    TxDart,
    TxHeadStart,
    TxEarlyHeadStart,
)
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.tx.emergency_medicaid.calculator import TxEmergencyMedicaid
from programs.programs.cross_white_label.medicaid.tx.for_children.calculator import TxMedicaidForChildren
from programs.programs.cross_white_label.medicaid.tx.for_parents_and_caretakers.calculator import (
    TxMedicaidForParentsAndCaretakers,
)
from programs.programs.cross_white_label.medicaid.tx.for_pregnant_women.calculator import TxMedicaidForPregnantWomen


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

    def test_pe_name_is_chip(self):
        """Test that TxChip has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(TxChip.pe_name, "chip")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxChip includes AgeDependency in pe_inputs."""
        from programs.framework.pe_dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxChip.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """Test that TxChip includes PregnancyDependency in pe_inputs."""
        from programs.framework.pe_dependencies.member import PregnancyDependency

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
        from programs.framework.pe_dependencies.member import Chip

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

    def test_pe_name_is_tx_harris_rides_eligible(self):
        """Test that TxHarrisCountyRides has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(TxHarrisCountyRides.pe_name, "tx_harris_rides_eligible")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that TxHarrisCountyRides includes AgeDependency in pe_inputs."""
        from programs.framework.pe_dependencies.member import AgeDependency

        self.assertIn(AgeDependency, TxHarrisCountyRides.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_is_disabled_dependency(self):
        """Test that TxHarrisCountyRides includes IsDisabledDependency in pe_inputs."""
        from programs.framework.pe_dependencies.member import IsDisabledDependency

        self.assertIn(IsDisabledDependency, TxHarrisCountyRides.pe_inputs)
        self.assertEqual(IsDisabledDependency.field, "is_disabled")

    def test_pe_inputs_includes_is_blind_dependency(self):
        """Test that TxHarrisCountyRides includes IsBlindDependency in pe_inputs."""
        from programs.framework.pe_dependencies.member import IsBlindDependency

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


class TestTxHeadStartWiring(TestCase):
    """
    TX-specific wiring for Head Start (ages 3-5) and Early Head Start (birth-3 /
    pregnant). Both are thin wrappers on the federal calculators, adding only the
    TX state code.

    The shared contract (pe_name, pe_outputs, no federal input dropped, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for
    all registered subclasses in ``federal/pe/tests/test_head_start.py``.
    """

    def test_head_start_pe_inputs_includes_tx_state_code(self):
        self.assertTrue(issubclass(TxHeadStart, HeadStart))
        self.assertIn(TxStateCodeDependency, TxHeadStart.pe_inputs)

    def test_early_head_start_pe_inputs_includes_tx_state_code(self):
        self.assertTrue(issubclass(TxEarlyHeadStart, EarlyHeadStart))
        self.assertIn(TxStateCodeDependency, TxEarlyHeadStart.pe_inputs)
