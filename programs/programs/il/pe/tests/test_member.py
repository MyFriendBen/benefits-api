"""
Unit tests for IL member-level PolicyEngine calculator classes.

These tests verify IL-specific calculator logic for member-level programs including:
- IlFamilyPlanningProgram calculator registration and configuration
- IL-specific pe_inputs (IlStateCodeDependency, IsFppMedicaidEligibleDependency)
- Behavior differences from base PolicyEngineMembersCalculator
"""

from django.test import TestCase

from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies import member, irs_gross_income
from programs.programs.policyengine.calculators.dependencies.household import IlStateCodeDependency
from programs.programs.il.pe import il_pe_calculators, il_member_calculators
from programs.programs.il.pe.member import IlFamilyPlanningProgram


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
        self.assertIn(member.TaxUnitHeadDependency, IlFamilyPlanningProgram.pe_inputs)
        self.assertEqual(member.TaxUnitHeadDependency.field, "is_tax_unit_head")

    def test_pe_inputs_includes_tax_unit_spouse_dependency(self):
        """Test that IlFamilyPlanningProgram includes TaxUnitSpouseDependency in pe_inputs."""
        self.assertIn(member.TaxUnitSpouseDependency, IlFamilyPlanningProgram.pe_inputs)
        self.assertEqual(member.TaxUnitSpouseDependency.field, "is_tax_unit_spouse")

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """Test that IlFamilyPlanningProgram includes PregnancyDependency in pe_inputs."""
        self.assertIn(member.PregnancyDependency, IlFamilyPlanningProgram.pe_inputs)
        self.assertEqual(member.PregnancyDependency.field, "is_pregnant")

    def test_pe_inputs_includes_is_fpp_medicaid_eligible_dependency(self):
        """Test that IlFamilyPlanningProgram includes IsFppMedicaidEligibleDependency in pe_inputs."""
        self.assertIn(member.IsFppMedicaidEligibleDependency, IlFamilyPlanningProgram.pe_inputs)
        self.assertEqual(member.IsFppMedicaidEligibleDependency.field, "is_medicaid_eligible")

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
        self.assertIn(member.IlFppEligible, IlFamilyPlanningProgram.pe_outputs)
        self.assertEqual(member.IlFppEligible.field, "il_fpp_eligible")


class TestIsFppMedicaidEligibleDependency(TestCase):
    """Tests for IsFppMedicaidEligibleDependency class."""

    def test_field_is_is_medicaid_eligible(self):
        """Test that the dependency field is correctly set."""
        self.assertEqual(member.IsFppMedicaidEligibleDependency.field, "is_medicaid_eligible")

    def test_dependencies_includes_insurance(self):
        """Test that the dependency requires insurance data."""
        self.assertIn("insurance", member.IsFppMedicaidEligibleDependency.dependencies)


class TestIlFppEligible(TestCase):
    """Tests for IlFppEligible output dependency class."""

    def test_field_is_il_fpp_eligible(self):
        """Test that the output dependency field is correctly set."""
        self.assertEqual(member.IlFppEligible.field, "il_fpp_eligible")
