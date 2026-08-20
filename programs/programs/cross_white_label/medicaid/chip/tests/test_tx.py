"""TX tests."""

from programs.programs.cross_white_label.medicaid.chip.tx import TxChip
from integrations.clients.policyengine.policy_engine import pe_input
from programs.programs.testing.pe_input_test_base import TxPeInputTestBase
from django.test import TestCase
from unittest.mock import MagicMock
from programs.programs.cross_white_label.medicaid.base import Medicaid
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household
from programs.framework.pe_dependencies import member


class TestTxChipPeInput(TxPeInputTestBase):
    """Tests for TxChip calculator pe_input dependencies."""

    def test_includes_all_pe_input_fields(self):
        """Test that pe_input includes all TxChip pe_inputs dependencies."""
        result = pe_input(self.screen, [TxChip])
        household = result["household"]
        people = household["people"]
        head_id = str(self.head.id)

        # Member-level dependencies
        self.assertIn("age", people[head_id])
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("is_disabled", people[head_id])
        self.assertIn("ssi_countable_resources", people[head_id])

        # Income dependencies
        income_fields = [
            "employment_income",
            "self_employment_income",
            "rental_income",
            "taxable_pension_income",
            "social_security",
        ]
        for field in income_fields:
            self.assertIn(field, people[head_id])

    def test_includes_pe_output_field(self):
        """Test that pe_input includes TxChip pe_outputs."""
        result = pe_input(self.screen, [TxChip])
        people = result["household"]["people"]

        for member_id in [str(self.head.id), str(self.spouse.id), str(self.child.id)]:
            self.assertIn("chip", people[member_id])

    def test_age_values_match_household_members(self):
        """Test that age values match HouseholdMember data."""
        result = pe_input(self.screen, [TxChip])
        people = result["household"]["people"]

        if people[str(self.head.id)]["age"]:
            period_key = list(people[str(self.head.id)]["age"].keys())[0]
            self.assertEqual(people[str(self.head.id)]["age"][period_key], 35)
            self.assertEqual(people[str(self.spouse.id)]["age"][period_key], 32)
            self.assertEqual(people[str(self.child.id)]["age"][period_key], 8)


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
