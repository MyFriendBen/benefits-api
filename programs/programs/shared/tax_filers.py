"""Who files a federal tax return, and how other members relate to the filers."""

from screener.models import HouseholdMember, Screen


def tax_filers(screen: Screen, joint: bool) -> list[HouseholdMember]:
    """
    The head of household and, on a joint return, the spouse.

    Matches the literal ``spouse`` relationship only: a domestic partner is neither a
    filer nor a dependent for federal tax.
    """
    members = screen.household_members.all()
    filers = [m for m in members if m.relationship == "headOfHousehold"]
    if joint:
        filers += [m for m in members if m.relationship == "spouse"]

    return filers


def is_younger(member: HouseholdMember, filer: HouseholdMember) -> bool:
    """
    Born in a later month than the filer. The screener has no day of birth, so a child
    born in the filer's own month doesn't count as younger. Falls back to comparing ages
    when either birth month is missing.
    """
    if member.birth_year_month is not None and filer.birth_year_month is not None:
        return member.birth_year_month > filer.birth_year_month

    member_age, filer_age = member.calc_age(), filer.calc_age()
    return member_age is not None and filer_age is not None and member_age < filer_age
