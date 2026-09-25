"""TX tests."""

from programs.programs.cross_white_label.wic.tx import TxWic
from django.test import TestCase


class TestTxWic(TestCase):
    """Tests for TxWic calculator class."""

    def test_pe_inputs_includes_the_wic_income_bundle(self):
        """TxWic inherits the WIC income sources from the parent Wic class.

        These replaced ``school_meal_countable_income``, which WIC's tree never read: TX WIC
        returned eligible at any reported income until the bundle landed. What the bundle
        covers is pinned in ``federal/pe/tests/test_wic.py``.
        """
        from programs.framework.pe_dependencies import wic_income
        from programs.framework.pe_dependencies.spm import SchoolMealCountableIncomeDependency

        for dep in wic_income:
            self.assertIn(dep, TxWic.pe_inputs)
        self.assertNotIn(SchoolMealCountableIncomeDependency, TxWic.pe_inputs)
