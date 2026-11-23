from datetime import date
from typing import Optional
from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.programs.shared.age import age_in_months

REFERENCE_DATE = date(2026, 11, 15)


def make_member(birth_year_month: Optional[date], age: Optional[int] = None) -> Mock:
    member = Mock()
    member.birth_year_month = birth_year_month
    member.calc_age.return_value = age
    return member


class TestAgeInMonths(SimpleTestCase):
    def test_born_this_month_is_month_zero(self) -> None:
        self.assertEqual(age_in_months(make_member(date(2026, 11, 1)), REFERENCE_DATE), 0)

    def test_counts_whole_months_across_years(self) -> None:
        self.assertEqual(age_in_months(make_member(date(2025, 6, 1)), REFERENCE_DATE), 17)

    def test_birth_month_later_in_the_year(self) -> None:
        self.assertEqual(age_in_months(make_member(date(2024, 12, 1)), REFERENCE_DATE), 23)

    def test_no_birth_month_falls_back_to_the_start_of_the_year_of_life(self) -> None:
        self.assertEqual(age_in_months(make_member(None, age=2), REFERENCE_DATE), 24)

    def test_no_birth_month_and_no_age_is_zero(self) -> None:
        self.assertEqual(age_in_months(make_member(None, age=None), REFERENCE_DATE), 0)
