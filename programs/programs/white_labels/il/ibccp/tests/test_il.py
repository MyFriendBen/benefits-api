"""IL tests."""

from programs.programs.white_labels.il.ibccp.calculator import IlBccp
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from unittest.mock import MagicMock
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from django.test import TestCase
from programs.framework.pe_dependencies import member as member_dependency
from programs.framework.pe_dependencies import member

IBCCP_SCREENING_VALUE = 400


class TestIlBccp(TestCase):
    """Tests for Illinois Breast and Cervical Cancer Program calculator."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlBccp is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlBccp, PolicyEngineMembersCalculator))

    def test_pe_name_is_il_bcc_eligible(self):
        """Test that IlBccp has the correct pe_name."""
        self.assertEqual(IlBccp.pe_name, "il_bcc_eligible")

    def test_pe_category_is_people(self):
        """Test that pe_category is set to 'people'."""
        self.assertEqual(IlBccp.pe_category, "people")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlBccp.pe_inputs)

    def test_pe_inputs_includes_age_dependency(self):
        """Test that AgeDependency is in pe_inputs (for age requirement)."""
        self.assertIn(member_dependency.AgeDependency, IlBccp.pe_inputs)

    def test_pe_inputs_includes_female_dependency(self):
        """Test that IlBccFemaleDependency is in pe_inputs."""
        self.assertIn(member_dependency.IlBccFemaleDependency, IlBccp.pe_inputs)

    def test_pe_inputs_includes_insurance_eligibility_dependency(self):
        """Test that HasBccQualifyingCoverageDependency is in pe_inputs."""
        self.assertIn(member_dependency.HasBccQualifyingCoverageDependency, IlBccp.pe_inputs)

    def test_pe_inputs_includes_receives_medicaid_dependency(self):
        """Test that ReceivesMedicaidDependency is in pe_inputs."""
        self.assertIn(member_dependency.ReceivesMedicaidDependency, IlBccp.pe_inputs)

    def test_pe_outputs_includes_il_bcc_eligible(self):
        """Test that IlBccEligible is in pe_outputs."""
        self.assertIn(member_dependency.IlBccEligible, IlBccp.pe_outputs)

    def test_member_value_returns_400_when_eligible(self):
        """
        Test that member_value returns $400 estimated screening value when eligible.
        This represents the average out-of-pocket cost for screening services.
        """
        calculator = IlBccp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        # Mock the parent class member_value to return True (eligible)
        calculator.get_member_variable = Mock(return_value=True)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        self.assertEqual(result, IBCCP_SCREENING_VALUE)

    def test_member_value_returns_zero_when_not_eligible(self):
        """Test that member_value returns 0 when not eligible."""
        calculator = IlBccp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock(return_value=False)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        self.assertEqual(result, 0)
