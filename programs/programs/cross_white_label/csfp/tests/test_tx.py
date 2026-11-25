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

    def test_pe_inputs_includes_the_tx_and_federal_v2_income_inputs(self):
        """From PE 2.145.6 Texas reads tx_dta_csfp_countable_income; the shared federal
        csfp_countable_income is inherited from the base calculator."""
        from programs.framework.pe_dependencies.spm import (
            CsfpCountableIncomeV2Dependency,
            TxDtaCsfpCountableIncomeDependency,
        )

        self.assertIn(CsfpCountableIncomeV2Dependency, TxCsfp.pe_inputs)
        self.assertIn(TxDtaCsfpCountableIncomeDependency, TxCsfp.pe_inputs)
