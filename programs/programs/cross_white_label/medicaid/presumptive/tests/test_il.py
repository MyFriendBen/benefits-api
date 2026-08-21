"""IL tests."""

from programs.programs.cross_white_label.medicaid.presumptive.il import IlMpe
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from unittest.mock import MagicMock
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from django.test import TestCase
from programs.framework.pe_dependencies import member as member_dependency
from programs.framework.pe_dependencies import member


class TestIlMpe(TestCase):
    """Tests for Illinois Medicaid Presumptive Eligibility for Pregnancy calculator."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlMpe is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlMpe, PolicyEngineMembersCalculator))

    def test_pe_name_is_il_mpe_eligible(self):
        """Test that IlMpe has the correct pe_name."""
        self.assertEqual(IlMpe.pe_name, "il_mpe_eligible")

    def test_pe_category_is_people(self):
        """Test that pe_category is set to 'people'."""
        self.assertEqual(IlMpe.pe_category, "people")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlMpe.pe_inputs)

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """Test that PregnancyDependency is in pe_inputs."""
        self.assertIn(member_dependency.PregnancyDependency, IlMpe.pe_inputs)

    def test_pe_inputs_includes_expected_children_dependency(self):
        """Test that ExpectedChildrenPregnancyDependency is in pe_inputs."""
        self.assertIn(member_dependency.ExpectedChildrenPregnancyDependency, IlMpe.pe_inputs)

    def test_pe_outputs_includes_il_mpe_eligible(self):
        """Test that IlMpeEligible is in pe_outputs."""
        self.assertIn(member_dependency.IlMpeEligible, IlMpe.pe_outputs)

    def test_member_value_returns_zero_when_has_medicaid(self):
        """Test that member_value returns 0 when member already has Medicaid."""
        calculator = IlMpe(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=True)  # Has Medicaid

        # Even if PE says eligible, having Medicaid disqualifies
        result = calculator.member_value(member)

        self.assertEqual(result, 0)
