"""Federal CSFP tests."""

from django.test import SimpleTestCase

from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
import programs.framework.pe_dependencies as dependency


class TestCsfpWiring(SimpleTestCase):
    def test_pe_inputs_includes_age(self):
        """CSFP is for people 60 and over; without age, no member is old enough to qualify."""
        self.assertIn(dependency.member.AgeDependency, CommoditySupplementalFoodProgram.pe_inputs)
