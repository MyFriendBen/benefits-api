"""IL tests."""

from programs.programs.cross_white_label.nslp.il import IlNslp
from django.test import TestCase


class TestIlNslp(TestCase):
    """Tests for Illinois National School Lunch Program calculator."""

    def test_uses_pe_net_subsidy_value(self):
        """IlNslp inherits the federal SchoolLunch value (PolicyEngine's
        school_meal_net_subsidy) rather than the removed hardcoded tier amounts."""
        self.assertEqual(IlNslp.pe_name, "school_meal_net_subsidy")
        self.assertFalse(hasattr(IlNslp, "tier_1_amount"))
        self.assertFalse(hasattr(IlNslp, "tier_2_amount"))
