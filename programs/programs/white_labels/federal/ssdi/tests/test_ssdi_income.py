"""
Income-test coverage for the federal Ssdi calculator.

The member income test compares monthly gross income against the SGA limit
($1,620, or $2,700 if visually impaired). It reads `("all",)`, so every income
type a member reports counts toward that threshold except those the calculator
excludes explicitly.

The Nurturing Futures direct cash payment is one such exclusion: the verified
income rules for that program list SSDI as having no direct impact. Without it,
a $600/month payment would flip a member with $1,020+ of other monthly income
from eligible to ineligible.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import MemberEligibility
from programs.programs.white_labels.federal.ssdi.calculator import Ssdi
from programs.util import Dependencies
from programs.framework.pe_dependencies import member

EARNED_TYPES = ("wages", "selfEmployment")


def make_calculator():
    screen = Mock()
    screen.household_members.all.return_value = []
    return Ssdi(screen, Mock(), {}, Dependencies())


def make_member(income, age=40, visually_impaired=False):
    """`income` is a dict of {income type: monthly amount}."""

    def calc_gross_income(frequency, types, exclude=[]):
        total = 0
        for income_type, amount in income.items():
            if income_type in exclude:
                continue
            bucket = "earned" if income_type in EARNED_TYPES else "unearned"
            if "all" in types or bucket in types or income_type in types:
                total += amount
        return total * (12 if frequency == "yearly" else 1)

    member = Mock()
    member.age = age
    member.visually_impaired = visually_impaired
    member.has_disability.return_value = True
    member.is_married.return_value = {"is_married": False}
    member.calc_gross_income = Mock(side_effect=calc_gross_income)
    return member


class TestSsdiIncomeTest(TestCase):
    def _run(self, income, **member_kwargs):
        e = MemberEligibility(make_member(income, **member_kwargs))
        make_calculator().member_eligible(e)
        return e.eligible

    # SGA limit is $1,620/month, compared with a strict `<`
    def test_income_below_the_sga_limit_is_eligible(self):
        self.assertTrue(self._run({"wages": 1_619}))

    def test_income_at_the_sga_limit_is_ineligible(self):
        self.assertFalse(self._run({"wages": 1_620}))

    def test_nurturing_futures_does_not_push_a_member_over_the_sga_limit(self):
        self.assertTrue(self._run({"wages": 1_020, "nurturingFutures": 600}))

    def test_a_counted_income_type_of_the_same_size_does_push_it_over(self):
        self.assertFalse(self._run({"wages": 1_020, "gifts": 600}))

    def test_nurturing_futures_alone_leaves_a_member_eligible(self):
        self.assertTrue(self._run({"nurturingFutures": 600}))

    def test_reported_ssdi_income_still_disqualifies(self):
        self.assertFalse(self._run({"sSDisability": 100}))
