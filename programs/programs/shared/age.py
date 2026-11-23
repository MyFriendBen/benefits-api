"""A member's age at finer than whole years."""

from datetime import date

from screener.models import HouseholdMember


def age_in_months(member: HouseholdMember, reference_date: date) -> int:
    """
    Whole months since the birth month on ``reference_date``, counting the birth
    month as month 0. A member with no birth month falls back to the stored age at the start
    of that year of life.
    """
    birth_year_month = member.birth_year_month
    if birth_year_month is None:
        return (member.calc_age() or 0) * 12

    return (reference_date.year - birth_year_month.year) * 12 + reference_date.month - birth_year_month.month
