"""
Unit tests for MA member-level PolicyEngine calculator classes.

These tests verify MA-specific calculator logic for member-level programs — the
state code each calculator adds and the slug it registers under. The wiring shared
across every state's Head Start lives in ``federal/pe/tests/test_head_start.py``.
"""

from django.test import TestCase

from programs.framework.pe_dependencies.household import MaStateCodeDependency
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.head_start.ma import MaHeadStart
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.early_head_start.ma import MaEarlyHeadStart


class TestMaHeadStartWiring(TestCase):
    """
    MA-specific wiring for Head Start (ages 3-5) and Early Head Start (birth-3 /
    pregnant). Both are thin wrappers on the federal calculators, adding only the
    MA state code.

    The shared contract (pe_name, pe_outputs, no federal input dropped, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for
    all registered subclasses in ``federal/pe/tests/test_head_start.py`` — including
    the ``member_value`` pass-through that this file previously exercised through
    mocks against the base class implementation.
    """

    def test_head_start_pe_inputs_includes_ma_state_code(self):
        self.assertTrue(issubclass(MaHeadStart, HeadStart))
        self.assertIn(MaStateCodeDependency, MaHeadStart.pe_inputs)

    def test_early_head_start_pe_inputs_includes_ma_state_code(self):
        self.assertTrue(issubclass(MaEarlyHeadStart, EarlyHeadStart))
        self.assertIn(MaStateCodeDependency, MaEarlyHeadStart.pe_inputs)
