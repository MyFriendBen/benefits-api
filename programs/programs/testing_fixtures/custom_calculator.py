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

from contextlib import contextmanager
from datetime import date
from typing import Callable, Optional, Union
from unittest.mock import Mock, patch

from django.test import TestCase

from integrations.clients.hud_income_limits import HudIncomeClientError

from programs.framework.base import Eligibility
from programs.util import Dependencies
from programs.programs.testing_fixtures.households import (
    add_expense,
    add_income,
    add_insurance,
    birth_year_month_for_age,
    make_program,
    make_white_label,
)
from screener.models import HouseholdMember, Insurance, Screen


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
    **kwargs,
) -> HouseholdMember:
    """Add a household member, and their income when the scenario states one.

    `monthly_income` and `yearly_income` describe a member by what they earn, at whichever
    frequency the scenario states — an annual figure is not divided down, because a limit
    tested at the boundary rarely survives the rounding. Both may be given. Call
    `add_income` directly for a second stream or a frequency other than these two.

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

    if monthly_income:
        add_income(household_member, monthly_income, income_type=income_type)

    if yearly_income:
        add_income(household_member, yearly_income, income_type=income_type, frequency="yearly")

    return household_member


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

    #: Where a household sits when the scenario does not say. Set these when a white label's
    #: programs are all local to one place, so a scenario names a location only to move away
    #: from it. Note that some white labels put a city in `county` — MA does (MFB-548).
    default_zipcode: str = ""
    default_county: str = ""

    #: Set when scenarios are written against a fixed calendar date rather than an age — a
    #: program start date, an enrollment window, a birth month copied from a spec. Ages built
    #: by `add_member` need no such pin, since they are derived against the same clock the
    #: calculator reads, but a literal `birth_year_month` drifts out of its window without one.
    reference_date: Optional[date] = None

    #: Set False when the calculator never reads `self.program` — no FPL or SMI lookup, no
    #: `program.year`. `self.program` is then a `Mock`, which skips the ~10 translated
    #: fields a real `Program` row writes per language.
    needs_program_row: bool = True

    # convenience re-exports so a subclass needs one import
    add_member = staticmethod(add_member)
    add_income = staticmethod(add_income)
    add_expense = staticmethod(add_expense)
    add_insurance = staticmethod(add_insurance)

    def make_screen(self, household_size: int = 1, **kwargs) -> Screen:
        """A household in this test case's white label.

        The white label, state and default location come from the class attributes, so a
        scenario names only what makes it distinct — its size, county, or assets.
        """
        kwargs.setdefault("white_label_code", self.white_label_code)
        kwargs.setdefault("state_code", self.state_code)
        kwargs.setdefault("zipcode", self.default_zipcode)
        kwargs.setdefault("county", self.default_county)

        return make_screen(household_size=household_size, **kwargs)

    @classmethod
    def setUpTestData(cls):
        """Create the white label and program once per class, not once per test.

        `Program.objects.new_program` writes a `Translation` row per translated field per
        language, so building it per test method dominates the runtime of a small suite.
        Neither row is mutated by a test, so one per class is enough.
        """
        super().setUpTestData()

        # The row this builds is what `has_benefit` and `program_eligible` look the program
        # up by, so a code that disagrees with the calculator's fails somewhere far from
        # here. Take the calculator's, and reject a subclass that contradicts it.
        expected = getattr(cls.calculator_class, "program_code", None)
        if expected:
            if cls.program_code == CustomCalculatorTestCase.program_code:
                cls.program_code = expected
            elif cls.program_code != expected:
                raise AssertionError(
                    f"{cls.__name__}.program_code is {cls.program_code!r} but "
                    f"{cls.calculator_class.__name__}.program_code is {expected!r}."
                )

        cls.white_label = make_white_label(cls.white_label_code, cls.state_code)
        if cls.needs_program_row:
            cls.program = make_program(cls.white_label_code, cls.program_code, cls.fpl_year, cls.state_code)
        else:
            cls.program = Mock()

    def setUp(self):
        """Freeze `Screen.get_reference_date` when the subclass pinned one."""
        super().setUp()

        if self.reference_date is None:
            return

        frozen = self.reference_date
        patcher = patch.object(Screen, "get_reference_date", lambda _self: frozen)
        patcher.start()
        self.addCleanup(patcher.stop)

    def hud_ami(self, *args, **kwargs):
        """`hud_ami` for this test case's calculator. See the module-level function."""
        return hud_ami(self.calculator_class, *args, **kwargs)

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


@contextmanager
def hud_ami(
    calculator_class: type,
    limit: Union[int, dict, Callable, None] = None,
    payment_standard: Union[int, None] = None,
    unavailable: bool = False,
    payment_standard_unavailable: bool = False,
):
    """Stand in for the HUD income-limit client while a calculator runs.

    A calculator reading an area median income asks `hud_client`, which is constructed at
    import time and calls HUD over the network. `limit` is the figure HUD would return for
    this household, so the scenario states an income limit the way it states an income.

    The client is bound per calculator module (`from ... import hud_client`), so the patch
    target follows `calculator_class`; patching the integration package would miss every
    calculator. All three lookups are stubbed, because a calculator choosing between the
    standard and the approximated limit is asserting on which one it called.

    `limit` may instead be a dict keyed by AMI percentage — `{"60%": 60_000, "80%": 80_000}`
    — for a calculator that compares a household against several bands. Any percentage not
    named returns 0.

    `limit` may also be a callable, which becomes the lookup's `side_effect` — for a test
    where what HUD was *asked* matters as much as what it returned.

    `payment_standard` is the ZIP-level SAFMR or metro FMR a voucher calculator reads
    through `get_screen_payment_standard`, which is a separate lookup from the AMI bands.

    `unavailable=True` raises `HudIncomeClientError` from the AMI lookups, and
    `payment_standard_unavailable=True` from the payment-standard lookup, for the tests
    covering what a calculator does when HUD is down. They are separate because a voucher
    calculator can survive losing one and not the other.

    Yields the mock, so a test can still assert on the call:

        with hud_ami(MaCha, 50_000) as hud:
            ...
            hud.get_screen_il_ami.assert_called_once_with(screen, "80%", "2025")

    HUD's own behaviour — request building, retries, error mapping — is covered by
    `integrations/clients/hud_income_limits/tests`, not here.
    """
    client = Mock()
    ami_lookups = ("get_screen_il_ami", "get_screen_mtsp_ami", "approximate_screen_mtsp_ami")

    if unavailable:
        error = HudIncomeClientError("HUD unavailable")
        for lookup in ami_lookups:
            getattr(client, lookup).side_effect = error
    elif callable(limit):
        # A stub that reads its arguments, for scenarios where the county, household size
        # or vintage HUD was asked about is itself the thing under test.
        for lookup in ami_lookups:
            getattr(client, lookup).side_effect = limit
    elif isinstance(limit, dict):
        # A calculator comparing a household against several AMI bands asks for each one.
        def by_percent(_screen, percent, *_args, **_kwargs):
            return limit.get(percent, 0)

        for lookup in ami_lookups:
            getattr(client, lookup).side_effect = by_percent
    else:
        for lookup in ami_lookups:
            getattr(client, lookup).return_value = limit

    if payment_standard_unavailable:
        client.get_screen_payment_standard.side_effect = HudIncomeClientError("HUD unavailable")
    else:
        client.get_screen_payment_standard.return_value = payment_standard

    with patch(f"{calculator_class.__module__}.hud_client", client):
        yield client


def eligible_result(value: int = 0) -> Eligibility:
    """An upstream program's verdict, for a calculator that gates on one.

    `value` lands on `household_value`, since `Eligibility.value` sums that with the members
    and is read-only.

    `ProgramCalculator.program_eligible` reads the results of programs already calculated,
    which the screener passes down as `data`. A test for a gated program supplies that
    verdict rather than calculating the upstream program for real:

        self.calculate(screen, data={"ks_medicaid": eligible_result()})
    """
    eligibility = Eligibility()
    eligibility.household_value = value

    return eligibility


def ineligible_result() -> Eligibility:
    """An upstream program the household did not qualify for. See `eligible_result`."""
    eligibility = Eligibility()
    eligibility.eligible = False

    return eligibility
