"""Household builders and a base test case for custom (MFB) calculator tests.

The PolicyEngine side of `pe_integration` builds a household for a recorded request,
so its ids are explicit and its amounts are verbatim from a spec scenario. A custom
calculator reads the same `Screen` but computes locally, so nothing here needs a fixed
primary key and a test can let Django assign them.

What a custom test needs, measured across the files that hand-roll a household today:
a white label always, an income stream usually, and a `Program` row carrying an FPL year
in the 13 files whose calculator reads one. The larger group — 76 files — stands up a
`Mock` program instead, because their calculators never touch it; those set
`needs_program_row = False` and skip the translation rows a real `Program` writes.
`CustomCalculatorTestCase` supplies all of it and runs the calculator, so a test reads as
household → assertion.
"""

from datetime import date
from typing import Optional
from unittest.mock import Mock

from django.test import TestCase
from django.utils import timezone

from programs.framework.base import Eligibility
from programs.models import FederalPoveryLimit, Program
from programs.util import Dependencies
from screener.models import Expense, HouseholdMember, IncomeStream, Insurance, Screen, WhiteLabel


def make_white_label(code: str = "test", state_code: str = "TS") -> WhiteLabel:
    """The white label a screen belongs to, created once and reused."""
    white_label, _ = WhiteLabel.objects.get_or_create(
        code=code, defaults={"name": code.upper(), "state_code": state_code}
    )
    return white_label


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


def add_member(screen: Screen, relationship: str = "headOfHousehold", age: float = 30, **kwargs) -> HouseholdMember:
    """Add a household member.

    `age` is stated as the scenario states it and may be fractional — `3.5` is three years
    six months, for the calculators that read `fraction_age()` rather than a whole-year age.
    Both `age` and a matching `birth_year_month` are set, so a calculator reading either
    field sees the same person.

    Pass `birth_year_month` explicitly instead when the scenario turns on an absolute
    calendar date rather than an age — a program start date or an enrollment window — since
    a birth month derived from today would drift out of that window as the calendar moves.
    Doing so leaves `age` alone, so pass that too if the calculator reads it.

    An `Insurance` row comes with the member, defaulting to uninsured, because the
    relation is one-to-one and non-null: a calculator reading `member.insurance` raises
    `RelatedObjectDoesNotExist` without it. Override with `add_insurance`.
    """
    if "birth_year_month" not in kwargs and age is not None:
        kwargs["birth_year_month"] = birth_year_month_for_age(age, screen.get_reference_date())

    household_member = HouseholdMember.objects.create(screen=screen, relationship=relationship, age=age, **kwargs)
    Insurance.objects.create(household_member=household_member)

    return household_member


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

    return insurance


def make_program(
    white_label_code: str = "test",
    name_abbreviated: str = "test_program",
    year: str = "2025",
    state_code: str = "TS",
) -> Program:
    """Create the `Program` row a calculator reads.

    `year` becomes `program.year`, which supplies the FPL table for any calculator doing
    a percent-of-poverty test. A calculator that reads `self.program.year.period` fails on
    an unsaved `Program`, which is why this returns a real row.

    The white label is created first because `Program.objects.new_program` looks it up
    rather than creating it.
    """
    make_white_label(white_label_code, state_code)
    fpl, _ = FederalPoveryLimit.objects.get_or_create(year=year, defaults={"period": year})

    program = Program.objects.new_program(white_label=white_label_code, name_abbreviated=name_abbreviated)
    program.year = fpl
    program.save()

    return program


class CustomCalculatorTestCase(TestCase):
    """Base for a custom calculator's tests.

    Parallels `PeIntegrationTestCase` on the PolicyEngine side: the subclass names its
    calculator and program, and `calculate()` runs it against a household the test built.

        class TestMyProgram(CustomCalculatorTestCase):
            calculator_class = MyProgram
            program_code = "co_my_program"

            def test_eligible_household(self):
                screen = self.make_screen(household_size=2, county="Denver County")
                add_income(self.add_member(screen), 1_500)

                e = self.calculate(screen)

                self.assertTrue(e.eligible)
                self.assertEqual(e.value, 1_200)
    """

    calculator_class: type = None
    program_code: str = "test_program"
    white_label_code: str = "test"
    state_code: str = "TS"
    fpl_year: str = "2025"

    #: Set False when the calculator never reads `self.program` — no FPL or SMI lookup, no
    #: `program.year`. `self.program` is then a `Mock`, which skips the ~10 translated
    #: fields a real `Program` row writes per language.
    needs_program_row: bool = True

    # convenience re-exports so a subclass needs one import
    make_screen = staticmethod(make_screen)
    add_member = staticmethod(add_member)
    add_income = staticmethod(add_income)
    add_expense = staticmethod(add_expense)
    add_insurance = staticmethod(add_insurance)

    @classmethod
    def setUpTestData(cls):
        """Create the white label and program once per class, not once per test.

        `Program.objects.new_program` writes a `Translation` row per translated field per
        language, so building it per test method dominates the runtime of a small suite.
        Neither row is mutated by a test, so one per class is enough.
        """
        super().setUpTestData()
        cls.white_label = make_white_label(cls.white_label_code, cls.state_code)
        if cls.needs_program_row:
            cls.program = make_program(cls.white_label_code, cls.program_code, cls.fpl_year, cls.state_code)
        else:
            cls.program = Mock()

    def make_calculator(self, screen: Screen, data: dict[str, Eligibility] = None, missing=()):
        """Build the calculator without running it.

        Use this to assert on one step rather than the whole result — `eligible()` for the
        household and member rules alone, or a program-specific method such as an income
        limit. `calculate()` covers the common case of wanting the final `Eligibility`.

        `data` is the results of programs already calculated, which a calculator gating on
        another program reads. `missing` names dependencies the screen does not supply, so
        a test can assert the program is skipped rather than valued wrongly.
        """
        return self.calculator_class(screen, self.program, data or {}, Dependencies(missing))

    def calculate(self, screen: Screen, data: dict[str, Eligibility] = None, missing=()) -> Eligibility:
        """Run the calculator end to end and return its `Eligibility`.

        Returns the `Eligibility` alone. A few suites predate this base class and define a
        local `calculate()` returning `(calculator, eligibility)` — `ma/bsp` is the one to
        check against when migrating a file that has its own helper of the same name, since
        unpacking the single return value fails loudly rather than silently.
        """
        return self.make_calculator(screen, data, missing).calc()
