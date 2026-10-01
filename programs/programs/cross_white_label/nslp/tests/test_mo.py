"""MO tests."""

from programs.programs.cross_white_label.nslp.mo import MoNslp
from programs.programs.cross_white_label.nslp.base import SchoolLunch
from django.test import TestCase


class TestMoNslpWiring(TestCase):
    """MoNslp registration and MO-specific pe_inputs handling."""

    def test_pe_name_is_school_meal_net_subsidy(self):
        """The annual net subsidy, not the per-day ``school_meal_daily_subsidy``."""
        self.assertEqual(MoNslp.pe_name, "school_meal_net_subsidy")

    # --- federal inputs must survive the MO override ---

    def test_pe_inputs_adds_exactly_one_input_over_federal(self):
        self.assertEqual(len(MoNslp.pe_inputs), len(SchoolLunch.pe_inputs) + 1)
