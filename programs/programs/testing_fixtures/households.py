"""Household builders shared by both engines' test fixtures.

A `Screen` and its members mean the same thing whichever engine values them, so the rows
themselves are built here and the engine-specific modules add only what their engine needs:
`pe_integration` requires explicit primary keys, because a cassette is replayable only
against the household it was recorded from, and `custom_calculator` does not.

Import these through the engine module a test already uses rather than from here, so a test
keeps one import and the engine's own rules stay in one place.
"""

from datetime import date
from typing import Optional

from django.utils import timezone

from programs.models import FederalPoveryLimit, Program
from screener.models import Expense, HouseholdMember, IncomeStream, Insurance, WhiteLabel


def make_white_label(code: str = "test", state_code: str = "TS") -> WhiteLabel:
    """The white label a screen belongs to, created once and reused."""
    white_label, _ = WhiteLabel.objects.get_or_create(
        code=code, defaults={"name": code.upper(), "state_code": state_code}
    )

    return white_label


def birth_year_month_for_age(age: float, reference_date: Optional[date] = None) -> date:
    """The birth month of someone `age` years old on `reference_date`.

    `HouseholdMember.age_from_date` treats the birth month as already attained
    (`reference_date.month >= birth_month` counts the whole year), so counting whole months
    back from the reference month lands on a birthday that has just happened. Reading the
    result back through `calc_age()` returns `age` again, whatever day the suite runs on:
    the reference month cancels out of both the derivation and the comparison.

    `age` may be fractional, in twelfths — `3.5` is three years six months. The model stores
    year and month only (`day` is always 1), so anything finer rounds to the nearest month.
    """
    months = round(age * 12)
    reference = reference_date or timezone.now().date()
    total = reference.year * 12 + reference.month - months

    return date((total - 1) // 12, (total - 1) % 12 + 1, 1)


def add_income(
    member: HouseholdMember,
    amount: int,
    income_type: str = "wages",
    frequency: str = "monthly",
) -> IncomeStream:
    """Give a member an income stream, stated as the scenario states it.

    `calc_gross_income` annualizes by frequency, so converting to a yearly figure here
    would hide what the scenario actually says.
    """
    return IncomeStream.objects.create(
        screen=member.screen,
        household_member=member,
        type=income_type,
        amount=amount,
        frequency=frequency,
    )


def add_expense(member: HouseholdMember, amount: int, expense_type: str = "rent", frequency: str = "monthly"):
    """Give a member an expense, for the programs that net it out of income."""
    return Expense.objects.create(
        screen=member.screen,
        household_member=member,
        type=expense_type,
        amount=amount,
        frequency=frequency,
    )


def add_insurance(member: HouseholdMember, **kwargs) -> Insurance:
    """Replace a member's insurance.

    `add_member` already gave them an uninsured record, so this overwrites it in place.
    Name only what the scenario needs — `medicaid=True, none=False` for a member already
    covered.
    """
    insurance, _ = Insurance.objects.update_or_create(household_member=member, defaults=kwargs)

    # `add_member` already read `member.insurance` into the relation cache, so a caller
    # asserting on it after this would otherwise still see the uninsured record.
    member.insurance = insurance

    return insurance


def make_program(
    white_label_code: str = "test",
    name_abbreviated: str = "test_program",
    year: str = "2025",
    state_code: str = "TS",
) -> Program:
    """Create the `Program` row a calculator reads.

    `year` becomes `program.year`, which supplies both the FPL table for a percent-of-poverty
    test and the `period` every PolicyEngine input and output is requested for. A calculator
    reading `self.program.year.period` fails on an unsaved `Program`, which is why this
    returns a real row.

    The white label is created first because `Program.objects.new_program` looks it up
    rather than creating it.
    """
    make_white_label(white_label_code, state_code)
    fpl, _ = FederalPoveryLimit.objects.get_or_create(year=year, defaults={"period": year})

    program = Program.objects.new_program(white_label=white_label_code, name_abbreviated=name_abbreviated)
    program.year = fpl
    program.save()

    return program
