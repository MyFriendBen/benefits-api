from datetime import date
from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import MemberEligibility
from programs.programs.white_labels.co.shitc.calculator import SeniorHousingIncomeTaxCredit
from programs.util import Dependencies
from screener.models import HouseholdMember


def make_calculator(tax_year=2025):
    program = Mock()
    program.year.period = str(tax_year)
    return SeniorHousingIncomeTaxCredit(Mock(), program, {}, Dependencies())


def make_head(age, birth_year_month=None):
    member = HouseholdMember(relationship="headOfHousehold", age=age, birth_year_month=birth_year_month)
    member.is_head = Mock(return_value=True)
    member.is_spouse = Mock(return_value=False)
    return member


class TestShitcAge(TestCase):
    """65 or older in the tax year the credit is claimed for, not on the screening date."""

    def _run(self, member, tax_year=2025):
        e = MemberEligibility(member)
        make_calculator(tax_year).member_eligible(e)
        return e.eligible

    def test_65_now_but_64_in_the_tax_year_is_ineligible(self):
        self.assertFalse(self._run(make_head(age=65, birth_year_month=date(1961, 3, 1))))

    def test_65_by_the_end_of_the_tax_year_is_eligible(self):
        self.assertTrue(self._run(make_head(age=65, birth_year_month=date(1960, 3, 1))))

    def test_without_a_birth_date_uses_the_stored_age(self):
        self.assertTrue(self._run(make_head(age=65)))
        self.assertFalse(self._run(make_head(age=64)))
