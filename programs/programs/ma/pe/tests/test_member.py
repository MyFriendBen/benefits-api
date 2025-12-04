"""
Unit tests for MA member-level PolicyEngine calculator classes.

These tests verify MA-specific calculator logic for member-level programs including:
- MaHeadStart calculator registration and configuration
- MA-specific pe_inputs (MaStateCodeDependency, income dependencies)
- PolicyEngine integration and value calculation
"""

from django.test import TestCase

from unittest.mock import Mock, MagicMock

from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies.household import MaStateCodeDependency
from programs.programs.ma.pe import ma_pe_calculators
from programs.programs.ma.pe.member import MaHeadStart, MaEarlyHeadStart


class TestMaHeadStart(TestCase):
    """Tests for MaHeadStart calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """
        Test that MaHeadStart calculator class exists and inherits correctly.

        This verifies the calculator has been set up in the codebase and follows the
        correct inheritance pattern for member-level calculators.
        """
        # Verify MaHeadStart is a subclass of PolicyEngineMembersCalculator
        self.assertTrue(issubclass(MaHeadStart, PolicyEngineMembersCalculator))

        # Verify it has the expected properties
        self.assertEqual(MaHeadStart.pe_name, "head_start")
        self.assertIsNotNone(MaHeadStart.pe_inputs)
        self.assertGreater(len(MaHeadStart.pe_inputs), 0)

    def test_is_registered_in_ma_pe_calculators(self):
        """Test that MA Head Start is registered in the calculators dictionary."""
        # Verify ma_head_start is in the calculators dictionary
        self.assertIn("ma_head_start", ma_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(ma_pe_calculators["ma_head_start"], MaHeadStart)

    def test_pe_inputs_includes_age_dependency(self):
        """
        Test that MaHeadStart includes AgeDependency in pe_inputs.

        Head Start eligibility requires age information (children ages 3-5).
        """
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, MaHeadStart.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_ma_state_code_dependency(self):
        """
        Test that MaStateCodeDependency is properly added to MA Head Start inputs.

        This is the key MA-specific dependency that sets state_code="MA" for
        PolicyEngine calculations.
        """
        # Verify MaStateCodeDependency is in pe_inputs
        self.assertIn(MaStateCodeDependency, MaHeadStart.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(MaStateCodeDependency.state, "MA")
        self.assertEqual(MaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_irs_gross_income_dependencies(self):
        """
        Test that MaHeadStart includes all IRS gross income dependencies.

        Head Start eligibility is based on household income relative to Federal
        Poverty Level, so all income types need to be captured.
        """
        from programs.programs.policyengine.calculators.dependencies import irs_gross_income

        # Verify all IRS gross income dependencies are included
        for income_dep in irs_gross_income:
            self.assertIn(income_dep, MaHeadStart.pe_inputs)

    def test_pe_outputs_includes_head_start_dependency(self):
        """
        Test that MaHeadStart has HeadStart dependency in pe_outputs.

        This is the PolicyEngine variable that returns the annual benefit value
        for eligible children.
        """
        from programs.programs.policyengine.calculators.dependencies.member import HeadStart

        self.assertIn(HeadStart, MaHeadStart.pe_outputs)

    def test_member_value_returns_policy_engine_value(self):
        """
        Test that member_value returns the PolicyEngine calculated value.

        Since MaHeadStart doesn't override member_value, it should use the base
        class implementation which returns the PolicyEngine value directly.
        """
        # Create a mock MaHeadStart calculator instance
        calculator = MaHeadStart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 12500
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member
        member = Mock()
        member.id = 1

        # Call member_value
        result = calculator.member_value(member)

        # Verify the result is the PolicyEngine value
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_returns_zero_when_not_eligible(self):
        """
        Test that member_value returns 0 when PolicyEngine determines ineligibility.

        If a child is not age-eligible or household is above income threshold,
        PolicyEngine will return 0.
        """
        # Create a mock MaHeadStart calculator instance
        calculator = MaHeadStart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine returning 0 (not eligible)
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock member
        member = Mock()
        member.id = 1

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0
        self.assertEqual(result, 0)

    def test_member_value_calls_get_member_variable_with_correct_id(self):
        """
        Test that member_value calls get_member_variable with the correct member ID.

        This verifies that the PolicyEngine value is fetched for the right member.
        """
        # Create a mock MaHeadStart calculator instance
        calculator = MaHeadStart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=10000)

        # Create a mock member with specific ID
        member = Mock()
        member.id = 42

        # Call member_value
        calculator.member_value(member)

        # Verify get_member_variable was called with the correct member ID
        calculator.get_member_variable.assert_called_once_with(42)

    def test_member_value_handles_varying_pe_values(self):
        """
        Test that member_value correctly returns different PolicyEngine values.

        PolicyEngine calculates state-specific per-child values based on
        state spending / enrollment, so values may vary.
        """
        # Create a mock MaHeadStart calculator instance
        calculator = MaHeadStart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock member
        member = Mock()
        member.id = 1

        # Test with different PolicyEngine values
        test_values = [0, 5000, 10655, 12000, 15000]

        for expected_value in test_values:
            calculator.get_member_variable = Mock(return_value=expected_value)
            result = calculator.member_value(member)
            self.assertEqual(result, expected_value)

    def test_calculator_has_no_custom_member_value_override(self):
        """
        Test that MaHeadStart doesn't override member_value method.

        This confirms we're using the base class implementation, which is the
        simplest approach for calculators that just need the raw PE value.
        """
        # Check that member_value is not defined in MaHeadStart's own __dict__
        self.assertNotIn("member_value", MaHeadStart.__dict__)

        # Verify it inherits from PolicyEngineMembersCalculator
        self.assertTrue(hasattr(MaHeadStart, "member_value"))

    def test_pe_inputs_has_required_dependencies(self):
        """
        Test that MaHeadStart has at least the minimum required dependencies.

        Should have: AgeDependency, MaStateCodeDependency, and IRS income dependencies.
        """
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        # Verify minimum required inputs are present
        self.assertGreaterEqual(len(MaHeadStart.pe_inputs), 7)

        # Verify required dependency types are present
        self.assertIn(AgeDependency, MaHeadStart.pe_inputs)
        self.assertIn(MaStateCodeDependency, MaHeadStart.pe_inputs)

    def test_head_start_dependency_field_name(self):
        """
        Test that HeadStart dependency has the correct field name.

        This should match the PolicyEngine variable name 'head_start'.
        """
        from programs.programs.policyengine.calculators.dependencies.member import HeadStart

        self.assertEqual(HeadStart.field, "head_start")

    def test_calculator_uses_member_category(self):
        """
        Test that MaHeadStart uses the 'people' category for PolicyEngine.

        Member-level calculators should inherit pe_category='people' from
        PolicyEngineMembersCalculator base class.
        """
        # Inherited from PolicyEngineMembersCalculator
        self.assertEqual(MaHeadStart.pe_category, "people")


class TestMaEarlyHeadStart(TestCase):
    """Tests for MaEarlyHeadStart calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """
        Test that MaEarlyHeadStart calculator class exists and inherits correctly.

        This verifies the calculator has been set up in the codebase and follows the
        correct inheritance pattern for member-level calculators.
        """
        # Verify MaEarlyHeadStart is a subclass of PolicyEngineMembersCalculator
        self.assertTrue(issubclass(MaEarlyHeadStart, PolicyEngineMembersCalculator))

        # Verify it has the expected properties
        self.assertEqual(MaEarlyHeadStart.pe_name, "early_head_start")
        self.assertIsNotNone(MaEarlyHeadStart.pe_inputs)
        self.assertGreater(len(MaEarlyHeadStart.pe_inputs), 0)

    def test_is_registered_in_ma_pe_calculators(self):
        """Test that MA Early Head Start is registered in the calculators dictionary."""
        # Verify ma_early_head_start is in the calculators dictionary
        self.assertIn("ma_early_head_start", ma_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(ma_pe_calculators["ma_early_head_start"], MaEarlyHeadStart)

    def test_pe_name_is_early_head_start(self):
        """Test that MaEarlyHeadStart has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(MaEarlyHeadStart.pe_name, "early_head_start")

    def test_pe_inputs_includes_age_dependency(self):
        """
        Test that MaEarlyHeadStart includes AgeDependency in pe_inputs.

        Early Head Start eligibility requires age information (children under 3).
        """
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, MaEarlyHeadStart.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_ma_state_code_dependency(self):
        """
        Test that MaStateCodeDependency is properly added to MA Early Head Start inputs.

        This is the key MA-specific dependency that sets state_code="MA" for
        PolicyEngine calculations.
        """
        # Verify MaStateCodeDependency is in pe_inputs
        self.assertIn(MaStateCodeDependency, MaEarlyHeadStart.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(MaStateCodeDependency.state, "MA")
        self.assertEqual(MaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_irs_gross_income_dependencies(self):
        """
        Test that MaEarlyHeadStart includes all IRS gross income dependencies.

        Early Head Start eligibility is based on household income relative to Federal
        Poverty Level, so all income types need to be captured.
        """
        from programs.programs.policyengine.calculators.dependencies import irs_gross_income

        # Verify all IRS gross income dependencies are included
        for income_dep in irs_gross_income:
            self.assertIn(income_dep, MaEarlyHeadStart.pe_inputs)

    def test_pe_outputs_includes_early_head_start_dependency(self):
        """
        Test that MaEarlyHeadStart has EarlyHeadStart dependency in pe_outputs.

        This is the PolicyEngine variable that returns the annual benefit value
        for eligible children.
        """
        from programs.programs.policyengine.calculators.dependencies.member import EarlyHeadStart

        self.assertIn(EarlyHeadStart, MaEarlyHeadStart.pe_outputs)

    def test_member_value_returns_policy_engine_value(self):
        """
        Test that member_value returns the PolicyEngine calculated value.

        Since MaEarlyHeadStart doesn't override member_value, it should use the base
        class implementation which returns the PolicyEngine value directly.
        """
        # Create a mock MaEarlyHeadStart calculator instance
        calculator = MaEarlyHeadStart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method to return a value
        pe_value = 15000
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member
        member = Mock()
        member.id = 1

        # Call member_value
        result = calculator.member_value(member)

        # Verify the result is the PolicyEngine value
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_returns_zero_when_not_eligible(self):
        """
        Test that member_value returns 0 when PolicyEngine determines ineligibility.

        If a child is not age-eligible or household is above income threshold,
        PolicyEngine will return 0.
        """
        # Create a mock MaEarlyHeadStart calculator instance
        calculator = MaEarlyHeadStart(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine returning 0 (not eligible)
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock member
        member = Mock()
        member.id = 1

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0
        self.assertEqual(result, 0)

    def test_early_head_start_dependency_field_name(self):
        """
        Test that EarlyHeadStart dependency has the correct field name.

        This should match the PolicyEngine variable name 'early_head_start'.
        """
        from programs.programs.policyengine.calculators.dependencies.member import EarlyHeadStart

        self.assertEqual(EarlyHeadStart.field, "early_head_start")

    def test_calculator_uses_member_category(self):
        """
        Test that MaEarlyHeadStart uses the 'people' category for PolicyEngine.

        Member-level calculators should inherit pe_category='people' from
        PolicyEngineMembersCalculator base class.
        """
        # Inherited from PolicyEngineMembersCalculator
        self.assertEqual(MaEarlyHeadStart.pe_category, "people")

    def test_pe_inputs_count(self):
        """
        Test that MaEarlyHeadStart has the expected number of pe_inputs.

        Should have: 1 AgeDependency + 1 MaStateCodeDependency + 5 IRS income dependencies = 7 total
        """
        # Count expected inputs
        # 1 Age + 1 State + 5 IRS income types
        expected_count = 7

        self.assertEqual(len(MaEarlyHeadStart.pe_inputs), expected_count)
