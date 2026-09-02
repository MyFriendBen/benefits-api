"""Recovered from pe/pe/tests."""

from django.test import TestCase
from programs.framework.pe_dependencies.household import MoStateCodeDependency
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.head_start.mo import MoHeadStart
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.early_head_start.mo import MoEarlyHeadStart


class TestMoHeadStartWiring(TestCase):
    """
    MO-specific wiring for Head Start (ages 3-5) and Early Head Start (birth-3 /
    pregnant). Both are thin wrappers on the federal calculators, adding only the
    MO state code.

    The shared contract (pe_name, pe_outputs, no federal input dropped, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for
    all registered subclasses in ``federal/pe/tests/test_head_start.py``.
    """

    def test_head_start_pe_inputs_includes_mo_state_code(self):
        self.assertTrue(issubclass(MoHeadStart, HeadStart))
        self.assertIn(MoStateCodeDependency, MoHeadStart.pe_inputs)

    def test_early_head_start_pe_inputs_includes_mo_state_code(self):
        self.assertTrue(issubclass(MoEarlyHeadStart, EarlyHeadStart))
        self.assertIn(MoStateCodeDependency, MoEarlyHeadStart.pe_inputs)
