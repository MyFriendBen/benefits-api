"""Household builders and a base test case for custom (MFB) calculator tests.

The PolicyEngine side of `pe_integration` builds a household for a recorded request,
so its ids are explicit and its amounts are verbatim from a spec scenario. A custom
calculator reads the same `Screen` but computes locally, so nothing here needs a fixed
primary key and a test can let Django assign them.

What a custom test does need, measured across the 25 files that hand-roll a household
today: an income stream (19 of them), a `Program` row carrying an FPL year (10), and
occasionally insurance or an expense. `CustomCalculatorTestCase` supplies all of it and
runs the calculator, so a test reads as household → assertion.
"""

from django.test import TestCase

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


def add_member(screen: Screen, relationship: str = "headOfHousehold", age: int = 30, **kwargs) -> HouseholdMember:
    """Add a household member.

    `age` is the field calculators read. `birth_year_month` derives `fraction_age()` for
    the programs that need a birthday rather than a whole-year age, so pass it as well
    when a scenario turns on one.

    An `Insurance` row comes with the member, defaulting to uninsured, because the
    relation is one-to-one and non-null: a calculator reading `member.insurance` raises
    `RelatedObjectDoesNotExist` without it. Override with `add_insurance`.
    """
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

    `add_member` already gave them an uninsured record, so this overwrites it. Name only
    what the scenario needs — `medicaid=True, none=False` for a member already covered.
    """
    Insurance.objects.filter(household_member=member).delete()

    return Insurance.objects.create(household_member=member, **kwargs)


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

    # convenience re-exports so a subclass needs one import
    make_screen = staticmethod(make_screen)
    add_member = staticmethod(add_member)
    add_income = staticmethod(add_income)
    add_expense = staticmethod(add_expense)
    add_insurance = staticmethod(add_insurance)

    def setUp(self):
        super().setUp()
        self.white_label = make_white_label(self.white_label_code, self.state_code)
        self.program = make_program(self.white_label_code, self.program_code, self.fpl_year, self.state_code)

    def calculate(self, screen: Screen, data: dict[str, Eligibility] = None, missing=()) -> Eligibility:
        """Run the calculator and return its `Eligibility`.

        `data` is the results of programs already calculated, which a calculator gating on
        another program reads. `missing` names dependencies the screen does not supply, so
        a test can assert the program is skipped rather than valued wrongly.
        """
        calculator = self.calculator_class(screen, self.program, data or {}, Dependencies(missing))

        return calculator.calc()
