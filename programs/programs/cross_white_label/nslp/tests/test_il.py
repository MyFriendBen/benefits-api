"""IL tests."""

from programs.programs.cross_white_label.nslp.il import IlNslp
from programs.framework.pe_dependencies.household import IlStateCodeDependency
from programs.programs.cross_white_label.nslp.base import SchoolLunch
from django.test import TestCase


class TestIlNslp(TestCase):
    """Tests for Illinois National School Lunch Program calculator."""

    def test_exists_and_is_subclass_of_school_lunch(self):
        """Test that IlNslp is a subclass of federal SchoolLunch."""
        self.assertTrue(issubclass(IlNslp, SchoolLunch))

    def test_pe_inputs_includes_il_state_code_dependency(self):
        """Test that IlStateCodeDependency is in pe_inputs."""
        self.assertIn(IlStateCodeDependency, IlNslp.pe_inputs)

    def test_pe_inputs_includes_all_parent_inputs(self):
        """Test that all parent SchoolLunch inputs are included."""
        for parent_input in SchoolLunch.pe_inputs:
            self.assertIn(parent_input, IlNslp.pe_inputs)

    def test_uses_pe_net_subsidy_value(self):
        """IlNslp inherits the federal SchoolLunch value (PolicyEngine's
        school_meal_net_subsidy) rather than the removed hardcoded tier amounts."""
        self.assertEqual(IlNslp.pe_name, "school_meal_net_subsidy")
        self.assertFalse(hasattr(IlNslp, "tier_1_amount"))
        self.assertFalse(hasattr(IlNslp, "tier_2_amount"))
