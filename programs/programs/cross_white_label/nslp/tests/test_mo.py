"""MO tests."""

from programs.programs.cross_white_label.nslp.mo import MoNslp
from programs.programs.cross_white_label.nslp.base import SchoolLunch
from django.test import TestCase
import programs.framework.pe_dependencies as dependency


class TestMoNslpWiring(TestCase):
    """MoNslp registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_school_lunch(self):
        self.assertTrue(issubclass(MoNslp, SchoolLunch))

    def test_pe_name_is_school_meal_net_subsidy(self):
        """The annual net subsidy, not the per-day ``school_meal_daily_subsidy``."""
        self.assertEqual(MoNslp.pe_name, "school_meal_net_subsidy")

    def test_pe_outputs_are_inherited_from_school_lunch(self):
        self.assertEqual(
            MoNslp.pe_outputs,
            [dependency.spm.SchoolMealNetSubsidy, dependency.spm.SchoolMealTier],
        )

    # --- the load-bearing input (over-eligibility regression guard) ---

    def test_pe_inputs_includes_mo_state_code(self):
        """Dropping this scores every MO household FREE tier at any income."""
        self.assertIn(dependency.household.MoStateCodeDependency, MoNslp.pe_inputs)

    # --- federal inputs must survive the MO override ---

    def test_pe_inputs_retains_all_federal_inputs(self):
        for federal_input in SchoolLunch.pe_inputs:
            self.assertIn(federal_input, MoNslp.pe_inputs)

    def test_pe_inputs_includes_school_meal_countable_income(self):
        self.assertIn(dependency.spm.SchoolMealCountableIncomeDependency, MoNslp.pe_inputs)

    def test_pe_inputs_includes_age(self):
        """PE derives ``is_in_k12_school`` from age; without it there are no K-12 children
        to value and the subsidy collapses to $0."""
        self.assertIn(dependency.member.AgeDependency, MoNslp.pe_inputs)

    def test_pe_inputs_adds_exactly_one_input_over_federal(self):
        self.assertEqual(len(MoNslp.pe_inputs), len(SchoolLunch.pe_inputs) + 1)
