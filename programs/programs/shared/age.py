"""A member's age at finer than whole years."""

from screener.models import HouseholdMember


def age_in_months(member: HouseholdMember) -> int:
    """
    Whole months since the birth month on the screen's reference date, counting the birth
    month as month 0. A member with no birth month falls back to the stored age at the start
    of that year of life.
    """
    birth_year_month = member.birth_year_month
    if birth_year_month is None:
        return (member.calc_age() or 0) * 12

    today = member.screen.get_reference_date()
    return (today.year - birth_year_month.year) * 12 + today.month - birth_year_month.month
