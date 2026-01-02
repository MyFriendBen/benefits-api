"""
Unit tests for MaCsfp PolicyEngine calculator class.

These tests verify MA-specific calculator logic for CSFP including:
- MaCsfp calculator registration and configuration
- MA-specific pe_inputs (MaStateCodeDependency)
- County filtering behavior
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.federal.pe.member import CommoditySupplementalFoodProgram
from programs.programs.policyengine.calculators.dependencies import household
from programs.programs.policyengine.calculators.dependencies.household import MaStateCodeDependency
from programs.programs.ma.pe import ma_pe_calculators
from programs.programs.ma.pe.member import MaCsfp


class TestMaCsfp(TestCase):
    """Tests for MaCsfp calculator class."""

    def test_exists_and_is_subclass_of_csfp(self):
        """
        Test that MaCsfp calculator class exists and is registered.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify MaCsfp is a subclass of CommoditySupplementalFoodProgram
        self.assertTrue(issubclass(MaCsfp, CommoditySupplementalFoodProgram))

        # Verify it has the expected properties
        self.assertEqual(MaCsfp.pe_name, "commodity_supplemental_food_program")
        self.assertIsNotNone(MaCsfp.pe_inputs)
        self.assertGreater(len(MaCsfp.pe_inputs), 0)

    def test_is_registered_in_ma_pe_calculators(self):
        """Test that MA CSFP is registered in the calculators dictionary."""
        # Verify ma_csfp is in the calculators dictionary
        self.assertIn("ma_csfp", ma_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(ma_pe_calculators["ma_csfp"], MaCsfp)

    def test_pe_inputs_includes_all_parent_inputs_plus_ma_specific(self):
        """
        Test that MaCsfp has all expected pe_inputs from parent and MA-specific.

        MaCsfp should inherit all inputs from parent CommoditySupplementalFoodProgram class plus add
        MA-specific dependencies like MaStateCodeDependency.
        """
        # MaCsfp should have all parent inputs plus MaStateCodeDependency
        self.assertGreater(len(MaCsfp.pe_inputs), len(CommoditySupplementalFoodProgram.pe_inputs))

        # Verify MaStateCodeDependency is in the list
        self.assertIn(household.MaStateCodeDependency, MaCsfp.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in CommoditySupplementalFoodProgram.pe_inputs:
            self.assertIn(parent_input, MaCsfp.pe_inputs)

    def test_pe_inputs_includes_ma_state_code_dependency(self):
        """
        Test that MaStateCodeDependency is properly added to MA CSFP inputs.

        This is the key MA-specific dependency that sets state_code="MA" for
        PolicyEngine calculations.
        """
        # Verify MaStateCodeDependency is in pe_inputs
        self.assertIn(MaStateCodeDependency, MaCsfp.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(MaStateCodeDependency.state, "MA")
        self.assertEqual(MaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_age_dependency(self):
        """Test that MaCsfp inherits AgeDependency from parent CommoditySupplementalFoodProgram class."""
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, MaCsfp.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_school_meal_countable_income_dependency(self):
        """Test that MaCsfp inherits SchoolMealCountableIncomeDependency from parent CommoditySupplementalFoodProgram class."""
        from programs.programs.policyengine.calculators.dependencies.spm import SchoolMealCountableIncomeDependency

        self.assertIn(SchoolMealCountableIncomeDependency, MaCsfp.pe_inputs)
        self.assertEqual(SchoolMealCountableIncomeDependency.field, "school_meal_countable_income")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that MaCsfp has the same pe_outputs as parent CommoditySupplementalFoodProgram class."""
        # MaCsfp should use the same outputs as parent
        self.assertEqual(MaCsfp.pe_outputs, CommoditySupplementalFoodProgram.pe_outputs)

    def test_eligible_counties_are_defined(self):
        """Test that MaCsfp has eligible counties defined."""
        expected_counties = [
            "Bristol",
            "Essex",
            "Middlesex",
            "Norfolk",
            "Plymouth",
            "Suffolk",
            "Worcester",
        ]
        self.assertEqual(MaCsfp.eligible_counties, expected_counties)

    def test_member_value_returns_pe_value_when_in_eligible_county(self):
        """
        Test that member_value returns PolicyEngine value when member is in eligible county.

        When a screen's county is in the eligible_counties list, the full
        PolicyEngine-calculated value should be returned.
        """
        # Create a mock MaCsfp calculator instance
        mock_screen = Mock()
        mock_screen.county = "Suffolk"  # Eligible county

        calculator = MaCsfp(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 600
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member
        member = Mock()
        member.id = 1

        # Call member_value
        result = calculator.member_value(member)

        # Verify the result is the PolicyEngine value
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_returns_zero_when_not_in_eligible_county(self):
        """
        Test that member_value returns 0 when member is not in eligible county.

        If the screen's county is not in the eligible_counties list, the member
        should not be eligible and member_value should return 0.
        """
        # Create a mock MaCsfp calculator instance
        mock_screen = Mock()
        mock_screen.county = "Berkshire"  # Not an eligible county

        calculator = MaCsfp(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 600
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member
        member = Mock()
        member.id = 1

        # Call member_value
        result = calculator.member_value(member)

        # Verify the result is 0 (county not eligible)
        self.assertEqual(result, 0)
        # get_member_variable should NOT be called because county check fails first
        calculator.get_member_variable.assert_not_called()

    def test_member_value_county_check_happens_before_pe_call(self):
        """
        Test that county eligibility check occurs before calling PolicyEngine.

        The county check should short-circuit and not make the PE API call
        if the county is not eligible.
        """
        # Create a mock MaCsfp calculator instance
        mock_screen = Mock()
        mock_screen.county = "Hampden"  # Not an eligible county

        calculator = MaCsfp(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=600)

        # Create a mock member
        member = Mock()
        member.id = 1

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 without calling PE
        self.assertEqual(result, 0)
        calculator.get_member_variable.assert_not_called()

    def test_member_value_with_each_eligible_county(self):
        """
        Test that member_value returns PE value for each eligible county.

        Verify all 7 eligible counties work correctly.
        """
        pe_value = 600

        for county in MaCsfp.eligible_counties:
            with self.subTest(county=county):
                mock_screen = Mock()
                mock_screen.county = county

                calculator = MaCsfp(mock_screen, Mock(), Mock())
                calculator._sim = MagicMock()
                calculator.get_member_variable = Mock(return_value=pe_value)

                member = Mock()
                member.id = 1

                result = calculator.member_value(member)
                self.assertEqual(result, pe_value)

    def test_member_value_with_zero_pe_value_and_eligible_county(self):
        """
        Test that member_value returns 0 when PolicyEngine returns 0, even in eligible county.

        If PolicyEngine determines no benefit value (e.g., member is under 60),
        it should be returned as-is even though county is eligible.
        """
        # Create a mock MaCsfp calculator instance
        mock_screen = Mock()
        mock_screen.county = "Suffolk"  # Eligible county

        calculator = MaCsfp(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock zero PolicyEngine value
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock member
        member = Mock()
        member.id = 1

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (PE says not eligible)
        self.assertEqual(result, 0)
