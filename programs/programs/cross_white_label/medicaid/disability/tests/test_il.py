"""IL tests."""

from programs.programs.cross_white_label.medicaid.disability.il_aabd import IlAabd
from programs.programs.cross_white_label.medicaid.disability.il_hbwd import IlHbwd
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from unittest.mock import MagicMock
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from django.test import TestCase
from programs.framework.pe_dependencies import member as member_dependency
from programs.framework.pe_dependencies import member

HBWD_ELIGIBLE_VALUE = 1


class TestIlAabd(TestCase):
    """Tests for Illinois Aid to the Aged, Blind, or Disabled calculator."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlAabd is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlAabd, PolicyEngineMembersCalculator))

    def test_pe_name_is_il_aabd_person(self):
        """Test that IlAabd has the correct pe_name."""
        self.assertEqual(IlAabd.pe_name, "il_aabd_person")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlAabd.pe_inputs)

    def test_pe_inputs_includes_age_dependency(self):
        """Test that AgeDependency is in pe_inputs."""
        self.assertIn(member_dependency.AgeDependency, IlAabd.pe_inputs)

    def test_pe_inputs_includes_disability_dependencies(self):
        """Test that disability dependencies are in pe_inputs."""
        self.assertIn(member_dependency.IsBlindDependency, IlAabd.pe_inputs)
        self.assertIn(member_dependency.IsDisabledDependency, IlAabd.pe_inputs)

    def test_pe_inputs_includes_income_dependencies(self):
        """Test that SSI income dependencies are in pe_inputs."""
        self.assertIn(member_dependency.SsiEarnedIncomeDependency, IlAabd.pe_inputs)

    def test_pe_inputs_includes_shelter_expense_dependencies(self):
        """Test that shelter expense dependencies are in pe_inputs."""
        self.assertIn(member_dependency.RentDependency, IlAabd.pe_inputs)

    def test_pe_outputs_includes_il_aabd(self):
        """Test that IlAabd output is in pe_outputs."""
        self.assertIn(member_dependency.IlAabd, IlAabd.pe_outputs)


class TestIlHbwd(TestCase):
    """Tests for Illinois Health Benefits for Workers with Disabilities calculator."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlHbwd is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlHbwd, PolicyEngineMembersCalculator))

    def test_pe_name_is_il_hbwd_person(self):
        """Test that IlHbwd has the correct pe_name."""
        self.assertEqual(IlHbwd.pe_name, "il_hbwd_person")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlHbwd.pe_inputs)

    def test_pe_inputs_includes_age_dependency(self):
        """Test that AgeDependency is in pe_inputs (for age 16-64 requirement)."""
        self.assertIn(member_dependency.AgeDependency, IlHbwd.pe_inputs)

    def test_pe_inputs_includes_disability_dependencies(self):
        """Test that disability dependencies are in pe_inputs."""
        self.assertIn(member_dependency.IsDisabledDependency, IlHbwd.pe_inputs)
        self.assertIn(member_dependency.SsdiReportedDependency, IlHbwd.pe_inputs)

    def test_pe_inputs_includes_earned_income_dependencies(self):
        """Test that earned income dependencies are in pe_inputs (employment requirement)."""
        self.assertIn(member_dependency.EmploymentIncomeDependency, IlHbwd.pe_inputs)
        self.assertIn(member_dependency.SelfEmploymentIncomeDependency, IlHbwd.pe_inputs)

    def test_pe_outputs_includes_il_hbwd_eligible(self):
        """Test that IlHbwdEligible is in pe_outputs."""
        self.assertIn(member_dependency.IlHbwdEligible, IlHbwd.pe_outputs)

    def test_pe_outputs_includes_il_hbwd_premium(self):
        """Test that IlHbwdPremium is in pe_outputs."""
        self.assertIn(member_dependency.IlHbwdPremium, IlHbwd.pe_outputs)

    def test_member_value_returns_one_when_eligible(self):
        """Test that member_value returns 1 when eligible (value displayed as 'Varies')."""
        calculator = IlHbwd(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_dependency_value = Mock(return_value=True)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        # Returns 1 to indicate eligible (value displayed as "Varies" in UI)
        self.assertEqual(result, HBWD_ELIGIBLE_VALUE)

    def test_member_value_returns_zero_when_not_eligible(self):
        """Test that member_value returns 0 when not eligible."""
        calculator = IlHbwd(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_dependency_value = Mock(return_value=False)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        self.assertEqual(result, 0)
