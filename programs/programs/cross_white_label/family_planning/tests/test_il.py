"""IL tests."""

from programs.programs.cross_white_label.family_planning.il_base import IlFamilyPlanningProgram
from programs.programs.cross_white_label.family_planning.il_ilfppe import IlFppe
from programs.programs.cross_white_label.family_planning.il_ilhfsfpp import IlHfsFpp
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from programs.framework.pe_base import PolicyEngineMembersCalculator
from django.test import TestCase
from integrations.clients.policyengine.registry import all_calculators
from programs.framework.pe_dependencies import irs_gross_income
from programs.framework.pe_dependencies import member as member_dependency


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

    def test_is_registered_for_hfs_fpp(self):
        """``il_hfs_fpp`` resolves to its own thin subclass of the shared FPP calculator."""
        self.assertIs(all_calculators["il_hfs_fpp"], IlHfsFpp)
        self.assertTrue(issubclass(IlHfsFpp, IlFamilyPlanningProgram))

    def test_is_registered_for_fppe(self):
        """``il_fppe`` resolves to its own thin subclass of the shared FPP calculator."""
        self.assertIs(all_calculators["il_fppe"], IlFppe)
        self.assertTrue(issubclass(IlFppe, IlFamilyPlanningProgram))

    def test_the_two_fpp_subclasses_do_not_diverge_from_the_shared_calculator(self):
        """Neither subclass overrides anything yet.

        ``il_hfs_fpp`` requires qualified immigration status and ``il_fppe`` does not,
        but PolicyEngine resolves both through the same ``il_fpp_eligible`` variable, so
        that distinction is unmodelled. The subclasses exist so the registry maps one key
        to one calculator. If the immigration-status requirement is ever modelled, this
        test is what will fail and force the change to be deliberate.
        """
        for sub in (IlHfsFpp, IlFppe):
            self.assertEqual(sub.pe_name, IlFamilyPlanningProgram.pe_name)
            self.assertEqual(list(sub.pe_inputs), list(IlFamilyPlanningProgram.pe_inputs))
            self.assertEqual(list(sub.pe_outputs), list(IlFamilyPlanningProgram.pe_outputs))

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
