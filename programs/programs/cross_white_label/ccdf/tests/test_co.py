"""
Unit tests for the ChildCareAssistance (cccap) calculator's income test.

CCCAP measures yearly gross household income, less child support paid, against the
county's own FPL percentage from a Google Sheet. Two income types are excluded from
that total: government cash assistance, and the Boulder County Nurturing Futures
direct cash payment (verified as not counted by CCCAP).

The screen's `calc_gross_income` is faked here rather than asserted on, so the tests
pin the eligibility outcome an excluded income type produces, not the call signature.
"""

from unittest.mock import Mock, patch

from django.test import TestCase

from programs.models import _FPL_DEFAULTS
from programs.framework.base import Eligibility
from programs.programs.cross_white_label.ccdf.co import ChildCareAssistance
from programs.util import Dependencies

FPL_2025 = _FPL_DEFAULTS["2025"]

COUNTY = "Denver County"
COUNTY_FPL_PERCENTS = {COUNTY: 185}


def make_calculator(income=None, household_size=1):
    """`income` is a dict of {income type: yearly amount}."""
    income = income or {}

    def calc_gross_income(frequency, types, exclude=[]):
        return sum(amount for t, amount in income.items() if t not in exclude)

    mock_program = Mock()
    mock_program.year.as_dict.return_value = FPL_2025

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.household_assets = 0
    mock_screen.calc_gross_income = Mock(side_effect=calc_gross_income)
    mock_screen.calc_expenses = Mock(return_value=0)

    return ChildCareAssistance(mock_screen, mock_program, {}, Dependencies())


class TestChildCareAssistanceIncomeExclusions(TestCase):
    def setUp(self):
        fpl_patcher = patch.object(ChildCareAssistance.fpl_limits, "get_data", return_value=dict(COUNTY_FPL_PERCENTS))
        fpl_patcher.start()
        self.addCleanup(fpl_patcher.stop)

        counties_patcher = patch(
            "programs.programs.cross_white_label.ccdf.co.counties_from_screen",
            return_value=[COUNTY],
        )
        counties_patcher.start()
        self.addCleanup(counties_patcher.stop)

    def _run(self, income):
        e = Eligibility()
        make_calculator(income=income).household_eligible(e)
        return e.eligible

    # 15,650 * 1.85 == 28,952.50
    def test_wages_under_the_limit_are_eligible(self):
        self.assertTrue(self._run({"wages": 28_952}))

    def test_wages_over_the_limit_are_ineligible(self):
        self.assertFalse(self._run({"wages": 28_953}))

    def test_nurturing_futures_does_not_push_a_household_over_the_limit(self):
        self.assertTrue(self._run({"wages": 28_000, "nurturingFutures": 7_200}))

    def test_cash_assistance_does_not_push_a_household_over_the_limit(self):
        self.assertTrue(self._run({"wages": 28_000, "cashAssistance": 7_200}))

    def test_a_counted_income_type_of_the_same_size_does_push_it_over(self):
        self.assertFalse(self._run({"wages": 28_000, "gifts": 7_200}))
