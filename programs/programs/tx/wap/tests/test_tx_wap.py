"""
Unit tests for TxWap calculator class.

Eligibility requirements:
- Household income <= 200% FPL, OR
- Categorical eligibility: SSI, TANF, or SNAP bypasses the income test
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.tx import tx_calculators
from programs.programs.tx.wap.calculator import TxWap
from programs.programs.calc import ProgramCalculator, Eligibility


def make_calculator(
    has_ssi=False,
    has_tanf=False,
    has_snap=False,
    household_income=0,
    household_size=1,
    fpl_limit=15_650,
):
    """Create a TxWap calculator with a mocked screen and program."""
    mock_program = Mock()
    mock_program.year.get_limit.return_value = fpl_limit

    benefit_map = {"ssi": has_ssi, "tanf": has_tanf, "snap": has_snap}
    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.has_benefit = Mock(side_effect=lambda b: benefit_map.get(b, False))
    mock_screen.calc_gross_income = Mock(return_value=household_income)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return TxWap(mock_screen, mock_program, {}, mock_missing_deps)


def run_household_eligible(calc):
    e = Eligibility()
    calc.household_eligible(e)
    return e.eligible


class TestTxWapClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TxWap, ProgramCalculator))

    def test_is_registered_in_tx_calculators(self):
        self.assertIn("tx_wap", tx_calculators)
        self.assertEqual(tx_calculators["tx_wap"], TxWap)

    def test_fpl_percent_is_2(self):
        self.assertEqual(TxWap.fpl_percent, 2)

    def test_amount_is_372(self):
        self.assertEqual(TxWap.amount, 372)


class TestTxWapIncomeEligibility(TestCase):
    """Income-only path: no categorical benefits."""

    def test_income_below_200_fpl_is_eligible(self):
        # 1-person: 2026 FPL = 15,960, limit = 31,920; income = 31,500
        calc = make_calculator(household_income=31_500, fpl_limit=15_960)
        self.assertTrue(run_household_eligible(calc))

    def test_income_exactly_at_200_fpl_is_eligible(self):
        # Boundary: income == limit (≤ is inclusive); 2026 1-person limit = 31,920
        calc = make_calculator(household_income=31_920, fpl_limit=15_960)
        self.assertTrue(run_household_eligible(calc))

    def test_income_above_200_fpl_is_ineligible(self):
        # 2026 1-person limit = 31,920; income = 31,921
        calc = make_calculator(household_income=31_921, fpl_limit=15_960)
        self.assertFalse(run_household_eligible(calc))

    def test_four_person_household_at_200_fpl_is_eligible(self):
        # 4-person: 2026 FPL = 33,000, limit = 66,000; income = 66,000
        calc = make_calculator(household_income=66_000, household_size=4, fpl_limit=33_000)
        self.assertTrue(run_household_eligible(calc))

    def test_three_person_household_just_above_200_fpl_is_ineligible(self):
        # 3-person: 2026 FPL = 27,320, limit = 54,640; income = 55,200 (just above)
        calc = make_calculator(household_income=55_200, household_size=3, fpl_limit=27_320)
        self.assertFalse(run_household_eligible(calc))


class TestTxWapCategoricalEligibility(TestCase):
    """Categorical benefits bypass the income test."""

    def test_snap_bypasses_income_test(self):
        calc = make_calculator(has_snap=True, household_income=99_999, fpl_limit=15_650)
        self.assertTrue(run_household_eligible(calc))

    def test_ssi_bypasses_income_test(self):
        calc = make_calculator(has_ssi=True, household_income=99_999, fpl_limit=15_650)
        self.assertTrue(run_household_eligible(calc))

    def test_tanf_bypasses_income_test(self):
        calc = make_calculator(has_tanf=True, household_income=99_999, fpl_limit=15_650)
        self.assertTrue(run_household_eligible(calc))

    def test_no_categorical_and_high_income_is_ineligible(self):
        calc = make_calculator(household_income=99_999, fpl_limit=15_650)
        self.assertFalse(run_household_eligible(calc))

    def test_priority_traits_do_not_override_income_ceiling(self):
        # High income, no categorical benefits — ineligible regardless of member traits
        # 3-person: 2026 FPL = 27,320, limit = 54,640; income = 75,600 (well above)
        calc = make_calculator(household_income=75_600, household_size=3, fpl_limit=27_320)
        self.assertFalse(run_household_eligible(calc))
