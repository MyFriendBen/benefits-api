"""
Unit tests for MaCsfp PolicyEngine calculator class.

These tests verify MA-specific calculator logic for CSFP including:
- MaCsfp calculator registration and configuration
- MA-specific pe_inputs (MaStateCodeDependency, MaCountyDependency)
"""

from django.test import TestCase

from programs.programs.federal.pe.member import CommoditySupplementalFoodProgram
from programs.programs.policyengine.calculators.dependencies import household
from programs.programs.policyengine.calculators.dependencies.household import MaStateCodeDependency, MaCountyDependency
from programs.programs.ma.pe import ma_pe_calculators
from programs.programs.ma.pe.member import MaCsfp


class TestMaCsfp(TestCase):
    """Tests for MaCsfp calculator class."""

    def test_exists_and_is_subclass_of_csfp(self):
        self.assertTrue(issubclass(MaCsfp, CommoditySupplementalFoodProgram))
        self.assertEqual(MaCsfp.pe_name, "commodity_supplemental_food_program")

    def test_is_registered_in_ma_pe_calculators(self):
        self.assertIn("ma_csfp", ma_pe_calculators)
        self.assertEqual(ma_pe_calculators["ma_csfp"], MaCsfp)

    def test_pe_inputs_includes_ma_state_code_dependency(self):
        self.assertIn(MaStateCodeDependency, MaCsfp.pe_inputs)
        self.assertEqual(MaStateCodeDependency.state, "MA")
        self.assertEqual(MaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_ma_county_dependency(self):
        self.assertIn(MaCountyDependency, MaCsfp.pe_inputs)
        self.assertEqual(MaCountyDependency.state_dependency_class, MaStateCodeDependency)

    def test_pe_inputs_includes_all_parent_inputs(self):
        for parent_input in CommoditySupplementalFoodProgram.pe_inputs:
            self.assertIn(parent_input, MaCsfp.pe_inputs)

    def test_pe_inputs_includes_age_dependency(self):
        from programs.programs.policyengine.calculators.dependencies.member import AgeDependency

        self.assertIn(AgeDependency, MaCsfp.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_school_meal_countable_income_dependency(self):
        from programs.programs.policyengine.calculators.dependencies.spm import SchoolMealCountableIncomeDependency

        self.assertIn(SchoolMealCountableIncomeDependency, MaCsfp.pe_inputs)
        self.assertEqual(SchoolMealCountableIncomeDependency.field, "school_meal_countable_income")

    def test_has_same_pe_outputs_as_parent(self):
        self.assertEqual(MaCsfp.pe_outputs, CommoditySupplementalFoodProgram.pe_outputs)
