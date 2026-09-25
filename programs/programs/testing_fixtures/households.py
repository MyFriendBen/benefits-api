"""Household builders shared by both engines' test fixtures.

A `Screen` and its members mean the same thing whichever engine values them, so the rows
themselves are built here and the engine-specific modules add only what their engine needs:
`pe_integration` requires explicit primary keys, because a cassette is replayable only
against the household it was recorded from, and `custom_calculator` does not. An explicit id
passes through `make_screen`/`add_member` as `id=`, like any other model field.

Import these through the engine module a test already uses rather than from here, so a test
keeps one import and the engine's own rules stay in one place.
"""

from datetime import date
from typing import Optional

from django.utils import timezone

from programs.models import FederalPoveryLimit, Program
from screener.models import Expense, HouseholdMember, IncomeStream, Insurance, Screen, WhiteLabel

#: What the screener sends for a member's condition checkboxes when none is ticked. The
#: model defaults them to null, which the screener never produces — and `missing_fields()`
#: reports a null as a missing dependency. The student follow-ups (`student_full_time`, …)
#: are left null, as the screener does for a member who is not a student.
SCREENER_MEMBER_DEFAULTS = {
    "student": False,
    "pregnant": False,
    "visually_impaired": False,
    "disabled": False,
    "long_term_disability": False,
    "was_in_foster_care": False,
}


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


def make_screen(
    white_label_code: str = "test",
    state_code: str = "TS",
    household_size: int = 1,
    zipcode: str = "",
    county: str = "",
    household_assets: int = 0,
    **kwargs,
) -> Screen:
    """A household to run a calculator against.

    `household_size` is what the calculator reads for FPL and SMI lookups, and it is
    not derived from the members added afterwards — a test that needs them to agree
    has to say so, because some scenarios deliberately disagree.

    `is_test=True` marks the row the way the screener marks its own test traffic. Nothing
    in the eligibility path reads it — only `set_screen_is_test`, the serializers, and the
    view filters — so it is a labelling convenience rather than a behavioural switch.
    """
    return Screen.objects.create(
        white_label=make_white_label(white_label_code, state_code),
        zipcode=zipcode,
        county=county,
        household_size=household_size,
        household_assets=household_assets,
        completed=False,
        is_test=True,
        **kwargs,
    )


def add_member(
    screen: Screen,
    relationship: str = "headOfHousehold",
    age: float = 30,
    monthly_income: int = 0,
    yearly_income: int = 0,
    income_type: str = "wages",
    stored_age: bool = True,
    screener_defaults: bool = True,
    **kwargs,
) -> HouseholdMember:
    """Add a household member, and their income when the scenario states one.

    `monthly_income` and `yearly_income` describe a member by what they earn, at whichever
    frequency the scenario states — an annual figure is not divided down, because a limit
    tested at the boundary rarely survives the rounding. Both may be given. Call
    `add_income` directly for a second stream or a frequency other than these two.

    `age` is stated as the scenario states it and may be fractional — `3.5` is three years
    six months, for the calculators that read `fraction_age()` rather than a whole-year age.
    `birth_year_month` is what the member's age is: `calc_age()` and `fraction_age()` derive
    it, and the stored `age` column is only a copy.

    Pass `birth_year_month` instead when the scenario turns on an absolute calendar date
    rather than an age — a program start date or an enrollment window — since a birth month
    derived from today would drift out of that window as the calendar moves. The stored
    `age` is then derived from it. Passing both is allowed only when they agree, so a member
    can never be two different people.

    The condition checkboxes (`student`, `pregnant`, `disabled`, …) default to False, as the
    screener sends them when none is ticked. Pass `None` explicitly for a row that lacks one.

    `stored_age=False` saves the member with a null `age`, as every member will be once the
    column is dropped, so a calculator still reading it fails in its own tests.

    An `Insurance` row comes with the member, defaulting to uninsured, because the
    relation is one-to-one and non-null: a calculator reading `member.insurance` raises
    `RelatedObjectDoesNotExist` without it. Override with `add_insurance`.

    `screener_defaults=False` skips the checkbox defaults, the derived `birth_year_month`, the
    `Insurance` row and the `has_income` reset, saving only what the caller passes. PolicyEngine
    cassettes were recorded from members built that way, and the request body they match on
    changes with any of these.
    """
    if screener_defaults:
        for field, default in SCREENER_MEMBER_DEFAULTS.items():
            kwargs.setdefault(field, default)

    reference_date = screen.get_reference_date()
    birth_year_month = kwargs.get("birth_year_month")

    if screener_defaults and "birth_year_month" not in kwargs and age is not None:
        kwargs["birth_year_month"] = birth_year_month_for_age(age, reference_date)
    elif birth_year_month is not None:
        derived = HouseholdMember.age_from_date(birth_year_month, reference_date)
        if age is None:
            age = derived
        elif int(age) != derived:
            raise ValueError(
                f"age={age} disagrees with birth_year_month={birth_year_month}, which is {derived} "
                f"on {reference_date}. Pass one of them."
            )

    # The screener sets `has_income` from the streams, which `add_income` mirrors. An explicit
    # value is reapplied afterwards, for a row written through the API that disagrees.
    explicit_has_income = kwargs.pop("has_income", None)

    household_member = HouseholdMember.objects.create(
        screen=screen,
        relationship=relationship,
        age=age if stored_age else None,
        has_income=False if screener_defaults else None,
        **kwargs,
    )
    if screener_defaults:
        Insurance.objects.create(household_member=household_member)

    if monthly_income:
        add_income(household_member, monthly_income, income_type=income_type)

    if yearly_income:
        add_income(household_member, yearly_income, income_type=income_type, frequency="yearly")

    if explicit_has_income is not None and household_member.has_income != explicit_has_income:
        household_member.has_income = explicit_has_income
        household_member.save(update_fields=["has_income"])

    return household_member


def set_age(member: HouseholdMember, age: Optional[float], stored_age: bool = True) -> HouseholdMember:
    """Change an existing member's age, keeping `birth_year_month` in step.

    Assigning `member.age` alone leaves the birth month saying otherwise, and `calc_age()`
    reads the birth month. `None` clears both, for a member whose age the screener lacks.
    """
    member.birth_year_month = None if age is None else birth_year_month_for_age(age, member.screen.get_reference_date())
    member.age = age if stored_age else None
    member.save(update_fields=["age", "birth_year_month"])

    return member


def add_income(
    member: HouseholdMember,
    amount: int,
    income_type: str = "wages",
    frequency: str = "monthly",
) -> IncomeStream:
    """Give a member an income stream, stated as the scenario states it.

    `calc_gross_income` annualizes by frequency, so converting to a yearly figure here
    would hide what the scenario actually says.

    Sets `has_income`, as the screener does for any member with a stream.
    """
    income = IncomeStream.objects.create(
        screen=member.screen,
        household_member=member,
        type=income_type,
        amount=amount,
        frequency=frequency,
    )

    if not member.has_income:
        member.has_income = True
        member.save(update_fields=["has_income"])

    return income


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
