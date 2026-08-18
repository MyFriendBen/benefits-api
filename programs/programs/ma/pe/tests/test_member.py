"""
Unit tests for MA member-level PolicyEngine calculator classes.

These tests verify MA-specific calculator logic for member-level programs — the
state code each calculator adds and the slug it registers under. The wiring shared
across every state's Head Start lives in ``federal/pe/tests/test_head_start.py``.
"""

from django.test import TestCase

from programs.programs.federal.pe.member import EarlyHeadStart, HeadStart
from programs.framework.pe_dependencies.household import MaStateCodeDependency
from programs.programs.ma.pe import ma_pe_calculators
from programs.programs.ma.pe.member import MaHeadStart, MaEarlyHeadStart


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

    def test_head_start_is_registered_as_ma_head_start(self):
        self.assertIs(ma_pe_calculators["ma_head_start"], MaHeadStart)

    def test_head_start_pe_inputs_includes_ma_state_code(self):
        self.assertTrue(issubclass(MaHeadStart, HeadStart))
        self.assertIn(MaStateCodeDependency, MaHeadStart.pe_inputs)

    def test_early_head_start_is_registered_as_ma_early_head_start(self):
        self.assertIs(ma_pe_calculators["ma_early_head_start"], MaEarlyHeadStart)

    def test_early_head_start_pe_inputs_includes_ma_state_code(self):
        self.assertTrue(issubclass(MaEarlyHeadStart, EarlyHeadStart))
        self.assertIn(MaStateCodeDependency, MaEarlyHeadStart.pe_inputs)
