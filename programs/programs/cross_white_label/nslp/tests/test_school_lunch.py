"""Federal school lunch tests."""

from django.test import SimpleTestCase

from programs.programs.cross_white_label.nslp.base import SchoolLunch
import programs.framework.pe_dependencies as dependency


class TestSchoolLunchWiring(SimpleTestCase):
    def test_pe_inputs_includes_age(self):
        """PE derives ``is_in_k12_school`` from age; without it there are no K-12 children
        to value and the subsidy collapses to $0."""
        self.assertIn(dependency.member.AgeDependency, SchoolLunch.pe_inputs)

    def test_pe_inputs_includes_school_meal_countable_income(self):
        """The tier is set by countable income; unsent, every household reads as $0 income
        and lands in the free tier."""
        self.assertIn(dependency.spm.SchoolMealCountableIncomeDependency, SchoolLunch.pe_inputs)
