"""
Unit tests for the NCFamilyPlanningServices (nc_fps) calculator's income test.

NC Family Planning Medicaid measures yearly gross household income against 195% FPL.
Both cash-assistance types are excluded from that total: this is a MAGI-based Medicaid
pathway, and PolicyEngine keeps `tanf` and `financial_assistance` out of
adjusted_gross_income, so counting either would measure the pathway against income the
pathway itself disregards.

The screen's `calc_gross_income` honours `exclude` here rather than being asserted on,
so the tests pin the eligibility outcome an excluded income type produces rather than
the call signature. The income limit comes from the real `FederalPoveryLimit.get_limit`,
which is pure arithmetic over the offline FPL table — no database, no network.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.models import FederalPoveryLimit
from programs.framework.base import Eligibility
from programs.programs.cross_white_label.family_planning.nc import NCFamilyPlanningServices
from programs.util import Dependencies

# Unsaved on purpose: `get_limit` only reads `self.period` and the cached FPL table.
FPL_2025 = FederalPoveryLimit(year="2025", period="2025")

# int(1.95 * 15,650) == 30,517 for a household of 1.
INCOME_LIMIT = 30_517


def make_calculator(income=None, household_size=1, medicaid_eligible=False):
    """`income` is a dict of {income type: yearly amount}."""
    income = income or {}

    def calc_gross_income(frequency, types, exclude=[]):
        return sum(amount for t, amount in income.items() if t not in exclude)

    mock_program = Mock()
    mock_program.year.get_limit = Mock(side_effect=FPL_2025.get_limit)

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(side_effect=calc_gross_income)

    medicaid = Eligibility()
    medicaid.eligible = medicaid_eligible

    return NCFamilyPlanningServices(mock_screen, mock_program, {"nc_medicaid": medicaid}, Dependencies())


class TestNCFamilyPlanningServicesIncomeExclusions(TestCase):
    def _run(self, income):
        e = Eligibility()
        make_calculator(income).household_eligible(e)
        return e.eligible

    def test_income_one_dollar_below_the_limit_is_eligible(self):
        self.assertTrue(self._run({"wages": INCOME_LIMIT - 1}))

    def test_income_exactly_at_the_limit_is_ineligible(self):
        # the comparison is strict `<`
        self.assertFalse(self._run({"wages": INCOME_LIMIT}))

    def test_cash_assistance_does_not_push_a_household_over_the_limit(self):
        self.assertTrue(self._run({"wages": 28_000, "cashAssistance": 7_200}))

    def test_cash_assistance_other_does_not_push_a_household_over_the_limit(self):
        # Non-TANF cash aid reaches PolicyEngine as `financial_assistance` rather than
        # `tanf`, but it is the same kind of money and is excluded on the same grounds.
        self.assertTrue(self._run({"wages": 28_000, "cashAssistanceOther": 7_200}))

    def test_a_counted_income_type_of_the_same_size_does_push_it_over(self):
        self.assertFalse(self._run({"wages": 28_000, "gifts": 7_200}))
