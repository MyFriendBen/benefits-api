"""
Unit tests for MaCsfp PolicyEngine calculator class.

These tests verify MA-specific calculator logic for CSFP including:
- MaCsfp calculator registration and configuration
- MA-specific pe_inputs (MaStateCodeDependency, MaCountyDependency)
"""

from django.test import TestCase

from programs.framework.pe_dependencies.household import (
    MaStateCodeDependency,
    MaCountyDependency,
)
from programs.programs.cross_white_label.csfp.ma import MaCsfp


class TestMaCsfp(TestCase):
    """Tests for MaCsfp calculator class."""

    def test_pe_inputs_includes_ma_county_dependency(self):
        self.assertIn(MaCountyDependency, MaCsfp.pe_inputs)
        self.assertEqual(MaCountyDependency.state_dependency_class, MaStateCodeDependency)

    def test_pe_inputs_includes_csfp_countable_income_dependency(self):
        from programs.framework.pe_dependencies.spm import (
            CsfpCountableIncomeDependency,
            SchoolMealCountableIncomeDependency,
        )

        self.assertIn(CsfpCountableIncomeDependency, MaCsfp.pe_inputs)
        self.assertNotIn(SchoolMealCountableIncomeDependency, MaCsfp.pe_inputs)
