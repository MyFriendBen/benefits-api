"""TX tests."""

from unittest.mock import MagicMock
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from django.test import TestCase
from programs.programs.white_labels.tx.harris_rides.calculator import TxHarrisCountyRides
from programs.framework.pe_dependencies.household import TxStateCodeDependency


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
