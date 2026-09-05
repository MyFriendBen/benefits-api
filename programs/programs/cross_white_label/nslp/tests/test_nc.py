"""NC tests."""

from programs.programs.cross_white_label.nslp.nc import NcNslp
from programs.programs.cross_white_label.nslp.base import SchoolLunch
from django.test import TestCase
import programs.framework.pe_dependencies as dependency


class TestNcNslpWiring(TestCase):
    """NcNslp registration and NC-specific pe_inputs handling."""

    def test_is_subclass_of_school_lunch(self):
        self.assertTrue(issubclass(NcNslp, SchoolLunch))

    def test_pe_name_is_school_meal_net_subsidy(self):
        """The annual net subsidy, not the per-day ``school_meal_daily_subsidy``."""
        self.assertEqual(NcNslp.pe_name, "school_meal_net_subsidy")

    def test_pe_outputs_are_inherited_from_school_lunch(self):
        self.assertEqual(
            NcNslp.pe_outputs,
            [dependency.spm.SchoolMealNetSubsidy, dependency.spm.SchoolMealTier],
        )

    # --- the load-bearing input (over-eligibility regression guard) ---

    def test_pe_inputs_includes_nc_state_code(self):
        """Dropping this scores every NC household FREE tier at any income (MFB-1683)."""
        self.assertIn(dependency.household.NcStateCodeDependency, NcNslp.pe_inputs)

    # --- federal inputs must survive the NC override ---

    def test_pe_inputs_retains_all_federal_inputs(self):
        for federal_input in SchoolLunch.pe_inputs:
            self.assertIn(federal_input, NcNslp.pe_inputs)

    def test_pe_inputs_includes_school_meal_countable_income(self):
        self.assertIn(dependency.spm.SchoolMealCountableIncomeDependency, NcNslp.pe_inputs)

    def test_pe_inputs_includes_age(self):
        """PE derives ``is_in_k12_school`` from age; without it there are no K-12 children
        to value and the subsidy collapses to $0."""
        self.assertIn(dependency.member.AgeDependency, NcNslp.pe_inputs)

    def test_pe_inputs_adds_exactly_one_input_over_federal(self):
        self.assertEqual(len(NcNslp.pe_inputs), len(SchoolLunch.pe_inputs) + 1)
