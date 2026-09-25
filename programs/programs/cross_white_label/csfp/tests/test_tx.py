"""TX tests."""

from programs.programs.cross_white_label.csfp.tx import TxCsfp
from django.test import TestCase


class TestTxCsfp(TestCase):
    """Tests for TxCsfp calculator class."""

    def test_pe_inputs_includes_csfp_countable_income_dependency(self):
        """Test that TxCsfp inherits CsfpCountableIncomeDependency from parent CommoditySupplementalFoodProgram class."""
        from programs.framework.pe_dependencies.spm import (
            CsfpCountableIncomeDependency,
            SchoolMealCountableIncomeDependency,
        )

        self.assertIn(CsfpCountableIncomeDependency, TxCsfp.pe_inputs)
        self.assertNotIn(SchoolMealCountableIncomeDependency, TxCsfp.pe_inputs)
