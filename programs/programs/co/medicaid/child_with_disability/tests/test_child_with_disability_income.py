"""
Income-test coverage for MedicaidChildWithDisability (`cwd_medicaid`).

This is a non-MAGI Medicaid pathway — it counts unearned income SSI-style rather
than through MAGI, so the Nurturing Futures direct cash payment is excluded from the
unearned side the same way it is for SSI itself. The verified income rules for that
program cover "MAGI-based Health First Colorado and CHP+" only, which is why this
pathway needed handling separately.

Household income test: (earned - $90 + unearned) * 0.67 <= 300% FPL.

`calc_gross_income` is faked with a real exclude-honoring implementation so the tests
pin eligibility outcomes rather than call signatures.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.models import _FPL_DEFAULTS
from programs.framework.base import Eligibility
from programs.programs.co.medicaid.child_with_disability.calculator import MedicaidChildWithDisability
from programs.util import Dependencies

FPL_2025 = _FPL_DEFAULTS["2025"]

EARNED_TYPES = ("wages", "selfEmployment")


def make_calculator(income=None, household_size=1):
    """`income` is a dict of {income type: yearly amount}."""
    income = income or {}

    def calc_gross_income(frequency, types, exclude=[]):
        total = 0
        for income_type, amount in income.items():
            if income_type in exclude:
                continue
            bucket = "earned" if income_type in EARNED_TYPES else "unearned"
            if "all" in types or bucket in types:
                total += amount
        return total

    program = Mock()
    program.year.as_dict.return_value = FPL_2025

    screen = Mock()
    screen.household_size = household_size
    screen.calc_gross_income = Mock(side_effect=calc_gross_income)

    return MedicaidChildWithDisability(screen, program, {}, Dependencies())


class TestChildWithDisabilityIncome(TestCase):
    def _run(self, income):
        e = Eligibility()
        make_calculator(income).household_eligible(e)
        return e.eligible

    # 15,650 * 3 == 46,950 limit; countable income is 67% of the total
    def test_unearned_income_under_the_limit_is_eligible(self):
        self.assertTrue(self._run({"pension": 70_000}))

    def test_unearned_income_over_the_limit_is_ineligible(self):
        self.assertFalse(self._run({"pension": 71_000}))

    def test_nurturing_futures_does_not_push_a_household_over_the_limit(self):
        self.assertTrue(self._run({"pension": 69_000, "nurturingFutures": 7_200}))

    def test_a_counted_unearned_type_of_the_same_size_does_push_it_over(self):
        self.assertFalse(self._run({"pension": 69_000, "gifts": 7_200}))
