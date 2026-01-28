"""
Unit tests for IL member-level PolicyEngine calculator classes.

These tests verify IL-specific calculator logic for member-level programs including:
- IlMsp (Medicare Savings Program) calculator
- IlAabd calculator
- IlHbwd calculator
- IlBccp (IBCCP) calculator
- IlMpe (Medicaid Presumptive Eligibility for Pregnancy) calculator
- IlFamilyPlanningProgram calculator
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies import member as member_dependency
from programs.programs.policyengine.calculators.dependencies import irs_gross_income
from programs.programs.policyengine.calculators.dependencies.household import IlStateCodeDependency
from programs.programs.il.pe import il_pe_calculators, il_member_calculators
from programs.programs.il.pe.member import (
    IlMsp,
    IlAabd,
    IlHbwd,
    IlBccp,
    IlMpe,
    IlFamilyPlanningProgram,
)


class TestIlMsp(TestCase):
    """Tests for Illinois Medicare Savings Program calculator."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlMsp is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlMsp, PolicyEngineMembersCalculator))

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlMsp is registered in the calculators dictionary."""
        self.assertIn("il_msp", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_msp"], IlMsp)

    def test_is_registered_in_il_member_calculators(self):
        """Test that IlMsp is registered in the member calculators dictionary."""
        self.assertIn("il_msp", il_member_calculators)
        self.assertEqual(il_member_calculators["il_msp"], IlMsp)

    def test_pe_name_is_msp(self):
        """Test that IlMsp has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(IlMsp.pe_name, "msp")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlMsp.pe_inputs)

    def test_pe_inputs_includes_medicare_eligibility(self):
        """Test that Medicare eligibility dependency is in pe_inputs."""
        self.assertIn(member_dependency.IsMedicareEligibleDependency, IlMsp.pe_inputs)

    def test_pe_inputs_includes_age_dependency(self):
        """Test that AgeDependency is in pe_inputs."""
        self.assertIn(member_dependency.AgeDependency, IlMsp.pe_inputs)

    def test_pe_inputs_includes_asset_dependency(self):
        """Test that CashAssetsDependency is in pe_inputs for asset limits."""
        from programs.programs.policyengine.calculators.dependencies import spm as spm_dependency

        self.assertIn(spm_dependency.CashAssetsDependency, IlMsp.pe_inputs)

    def test_pe_outputs_includes_msp_eligible(self):
        """Test that MspEligible is in pe_outputs."""
        self.assertIn(member_dependency.MspEligible, IlMsp.pe_outputs)

    def test_pe_outputs_includes_msp_category(self):
        """Test that MspCategory is in pe_outputs."""
        self.assertIn(member_dependency.MspCategory, IlMsp.pe_outputs)

    def test_pe_outputs_includes_msp_value(self):
        """Test that Msp value dependency is in pe_outputs."""
        self.assertIn(member_dependency.Msp, IlMsp.pe_outputs)

    def test_member_value_returns_yearly_benefit(self):
        """Test that member_value returns yearly benefit (monthly * 12)."""
        calculator = IlMsp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_dependency_value = Mock(return_value=True)
        calculator.get_member_variable = Mock(return_value=185.0)  # Part B premium

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        # Monthly benefit * 12
        self.assertEqual(result, int(185.0 * 12))

    def test_member_value_returns_zero_when_not_eligible(self):
        """Test that member_value returns 0 when not eligible."""
        calculator = IlMsp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_dependency_value = Mock(return_value=False)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        self.assertEqual(result, 0)


class TestIlAabd(TestCase):
    """Tests for Illinois Aid to the Aged, Blind, or Disabled calculator."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlAabd is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlAabd, PolicyEngineMembersCalculator))

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlAabd is registered in the calculators dictionary."""
        self.assertIn("il_aabd", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_aabd"], IlAabd)

    def test_is_registered_in_il_member_calculators(self):
        """Test that IlAabd is registered in the member calculators dictionary."""
        self.assertIn("il_aabd", il_member_calculators)
        self.assertEqual(il_member_calculators["il_aabd"], IlAabd)

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

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlHbwd is registered in the calculators dictionary."""
        self.assertIn("il_hbwd", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_hbwd"], IlHbwd)

    def test_is_registered_in_il_member_calculators(self):
        """Test that IlHbwd is registered in the member calculators dictionary."""
        self.assertIn("il_hbwd", il_member_calculators)
        self.assertEqual(il_member_calculators["il_hbwd"], IlHbwd)

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
        self.assertEqual(result, 1)

    def test_member_value_returns_zero_when_not_eligible(self):
        """Test that member_value returns 0 when not eligible."""
        calculator = IlHbwd(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_dependency_value = Mock(return_value=False)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        self.assertEqual(result, 0)


class TestIlBccp(TestCase):
    """Tests for Illinois Breast and Cervical Cancer Program calculator."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlBccp is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlBccp, PolicyEngineMembersCalculator))

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlBccp is registered in the calculators dictionary."""
        self.assertIn("il_ibccp", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_ibccp"], IlBccp)

    def test_is_registered_in_il_member_calculators(self):
        """Test that IlBccp is registered in the member calculators dictionary."""
        self.assertIn("il_ibccp", il_member_calculators)
        self.assertEqual(il_member_calculators["il_ibccp"], IlBccp)

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
        """Test that IlBccInsuranceEligibleDependency is in pe_inputs."""
        self.assertIn(member_dependency.IlBccInsuranceEligibleDependency, IlBccp.pe_inputs)

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

        self.assertEqual(result, 400)

    def test_member_value_returns_zero_when_not_eligible(self):
        """Test that member_value returns 0 when not eligible."""
        calculator = IlBccp(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock(return_value=False)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        self.assertEqual(result, 0)


class TestIlMpe(TestCase):
    """Tests for Illinois Medicaid Presumptive Eligibility for Pregnancy calculator."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that IlMpe is a subclass of PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(IlMpe, PolicyEngineMembersCalculator))

    def test_is_registered_in_il_pe_calculators(self):
        """Test that IlMpe is registered in the calculators dictionary."""
        self.assertIn("il_mpe", il_pe_calculators)
        self.assertEqual(il_pe_calculators["il_mpe"], IlMpe)

    def test_is_registered_in_il_member_calculators(self):
        """Test that IlMpe is registered in the member calculators dictionary."""
        self.assertIn("il_mpe", il_member_calculators)
        self.assertEqual(il_member_calculators["il_mpe"], IlMpe)

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


class TestIlFamilyPlanningProgram(TestCase):
    """Tests for IlFamilyPlanningProgram calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """
        Test that IlFamilyPlanningProgram calculator class exists and inherits from PolicyEngineMembersCalculator.

        This verifies the calculator has been set up in the codebase and follows the
        correct inheritance pattern for member-level calculators.
        """
        # Verify IlFamilyPlanningProgram is a subclass of PolicyEngineMembersCalculator
        self.assertTrue(issubclass(IlFamilyPlanningProgram, PolicyEngineMembersCalculator))

        # Verify it has the expected properties
        self.assertEqual(IlFamilyPlanningProgram.pe_name, "il_fpp_eligible")
        self.assertIsNotNone(IlFamilyPlanningProgram.pe_inputs)
        self.assertGreater(len(IlFamilyPlanningProgram.pe_inputs), 0)

    def test_is_registered_in_il_pe_calculators_for_hfs_fpp(self):
        """Test that IL HFS FPP is registered in the calculators dictionary."""
        # Verify il_hfs_fpp is in the calculators dictionary
        self.assertIn("il_hfs_fpp", il_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(il_pe_calculators["il_hfs_fpp"], IlFamilyPlanningProgram)

    def test_is_registered_in_il_pe_calculators_for_fppe(self):
        """Test that IL FPPE is registered in the calculators dictionary."""
        # Verify il_fppe is in the calculators dictionary
        self.assertIn("il_fppe", il_pe_calculators)

        # Verify it points to the correct class
        self.assertEqual(il_pe_calculators["il_fppe"], IlFamilyPlanningProgram)

    def test_is_registered_in_il_member_calculators(self):
        """Test that both FPP programs are registered in the member calculators dictionary."""
        self.assertIn("il_hfs_fpp", il_member_calculators)
        self.assertIn("il_fppe", il_member_calculators)
        self.assertEqual(il_member_calculators["il_hfs_fpp"], IlFamilyPlanningProgram)
        self.assertEqual(il_member_calculators["il_fppe"], IlFamilyPlanningProgram)

    def test_pe_name_is_il_fpp_eligible(self):
        """Test that IlFamilyPlanningProgram has the correct pe_name for PolicyEngine API calls."""
        self.assertEqual(IlFamilyPlanningProgram.pe_name, "il_fpp_eligible")

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """
        Test that IlStateCodeDependency is properly added to IL FPP inputs.

        This is the key IL-specific dependency that sets state_code="IL" for
        PolicyEngine calculations.
        """
        # Verify IlStateCodeDependency is in pe_inputs
        self.assertIn(IlStateCodeDependency, IlFamilyPlanningProgram.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(IlStateCodeDependency.state, "IL")
        self.assertEqual(IlStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_tax_unit_head_dependency(self):
        """Test that IlFamilyPlanningProgram includes TaxUnitHeadDependency in pe_inputs."""
        self.assertIn(member_dependency.TaxUnitHeadDependency, IlFamilyPlanningProgram.pe_inputs)
        self.assertEqual(member_dependency.TaxUnitHeadDependency.field, "is_tax_unit_head")

    def test_pe_inputs_includes_tax_unit_spouse_dependency(self):
        """Test that IlFamilyPlanningProgram includes TaxUnitSpouseDependency in pe_inputs."""
        self.assertIn(member_dependency.TaxUnitSpouseDependency, IlFamilyPlanningProgram.pe_inputs)
        self.assertEqual(member_dependency.TaxUnitSpouseDependency.field, "is_tax_unit_spouse")

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """Test that IlFamilyPlanningProgram includes PregnancyDependency in pe_inputs."""
        self.assertIn(member_dependency.PregnancyDependency, IlFamilyPlanningProgram.pe_inputs)
        self.assertEqual(member_dependency.PregnancyDependency.field, "is_pregnant")

    def test_pe_inputs_includes_irs_gross_income_dependencies(self):
        """
        Test that IlFamilyPlanningProgram includes all irs_gross_income dependencies.

        The FPP program needs income information for eligibility determination.
        """
        for income_dependency in irs_gross_income:
            self.assertIn(
                income_dependency,
                IlFamilyPlanningProgram.pe_inputs,
                f"Expected {income_dependency.__name__} from irs_gross_income in pe_inputs",
            )

    def test_pe_outputs_includes_il_fpp_eligible(self):
        """Test that IlFamilyPlanningProgram has IlFppEligible dependency in pe_outputs."""
        self.assertIn(member_dependency.IlFppEligible, IlFamilyPlanningProgram.pe_outputs)
        self.assertEqual(member_dependency.IlFppEligible.field, "il_fpp_eligible")


class TestIlFppEligible(TestCase):
    """Tests for IlFppEligible output dependency class."""

    def test_field_is_il_fpp_eligible(self):
        """Test that the output dependency field is correctly set."""
        self.assertEqual(member_dependency.IlFppEligible.field, "il_fpp_eligible")
