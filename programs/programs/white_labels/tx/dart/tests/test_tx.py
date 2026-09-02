"""TX tests."""

from unittest.mock import MagicMock
from programs.programs.cross_white_label.medicaid.base import Medicaid
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from django.test import TestCase
from programs.programs.white_labels.tx.dart.calculator import TxDart
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import member


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
