from collections.abc import Collection
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property

from sentry_sdk import capture_message

from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.white_labels.federal.tax import UNTAXED_INCOME_TYPES
from screener.models import HouseholdMember


@dataclass(frozen=True)
class EitcColumn:
    """One column of the EIC Table: a filing status and a number of qualifying children."""

    phase_in_rate: Decimal
    earned_income_amount: int
    max_credit: int
    phase_out_rate: Decimal
    phase_out_start: int
    # The completed phase-out amount: earned income and AGI must be below it.
    limit: int


@dataclass(frozen=True)
class EitcYear:
    investment_income_limit: int
    # Keyed by (qualifying children, capped at 3; married filing jointly).
    columns: dict[tuple[int, bool], EitcColumn]


def _columns(
    phase_in_rate: str,
    earned_income_amount: int,
    max_credit: int,
    phase_out_rate: str,
    phase_out_start: tuple[int, int],
    limit: tuple[int, int],
) -> dict[bool, EitcColumn]:
    """The single and joint columns for one number of children, which differ only in where
    the phase-out starts and ends."""
    return {
        joint: EitcColumn(
            Decimal(phase_in_rate),
            earned_income_amount,
            max_credit,
            Decimal(phase_out_rate),
            phase_out_start[joint],
            limit[joint],
        )
        for joint in (False, True)
    }


def _year(investment_income_limit: int, by_children: dict[int, dict[bool, EitcColumn]]) -> EitcYear:
    return EitcYear(
        investment_income_limit,
        {(n, joint): column for n, columns in by_children.items() for joint, column in columns.items()},
    )


# Rev. Proc. 2024-40 § 2.06; rates from 26 U.S.C. § 32(b)(1). Phase-out start and limit are
# (not joint, joint).
EITC_YEARS: dict[int, EitcYear] = {
    2025: _year(
        11_950,
        {
            0: _columns("0.0765", 8_490, 649, "0.0765", (10_620, 17_730), (19_104, 26_214)),
            1: _columns("0.34", 12_730, 4_328, "0.1598", (23_350, 30_470), (50_434, 57_554)),
            2: _columns("0.40", 17_880, 7_152, "0.2106", (23_350, 30_470), (57_310, 64_430)),
            3: _columns("0.45", 17_880, 8_046, "0.2106", (23_350, 30_470), (61_555, 68_675)),
        },
    ),
}

TABLE_BRACKET = 50


def eic_table(amount: float, column: EitcColumn) -> int:
    """
    The EIC Table's credit for ``amount``, which the IRS publishes in $50 rows rather than
    as a formula (26 U.S.C. § 32(f)).

    Each row is priced at its midpoint and rounded to the dollar. A row holding the end of
    the phase-in or the start of the phase-out pays the maximum, and the last row of a column
    stops at the limit, so its midpoint is that of the narrower range the table's footnotes
    give. This reproduces every row and footnote of the 2025 table.
    """
    if amount <= 0 or amount >= column.limit:
        return 0

    low = int(amount) // TABLE_BRACKET * TABLE_BRACKET
    high = min(low + TABLE_BRACKET, column.limit)
    # The table's first row runs from $1, not $0.
    low = max(low, 1)

    if low <= column.earned_income_amount < high or low < column.phase_out_start < high:
        return column.max_credit

    midpoint = Decimal(low + high) / 2
    max_credit = Decimal(column.max_credit)
    phased_in = column.phase_in_rate * midpoint
    phased_out = max_credit - column.phase_out_rate * max(midpoint - column.phase_out_start, 0)
    credit = max(min(phased_in, max_credit, phased_out), Decimal(0))

    return int(credit.quantize(Decimal(1), rounding=ROUND_HALF_UP))


class FederalEitc(ProgramCalculator):
    """
    Federal Earned Income Tax Credit (26 U.S.C. § 32), read off the IRS's EIC Table for the
    program's tax year.

    The filers are the head and, on a joint return, the member recorded as their spouse.
    Only their income counts, so a roommate's wages stay off the return. A qualifying child
    is any other member who is the head's child, stepchild, foster child, grandchild or
    sibling, and who is disabled, or younger than a filer and under 19 at the end of the
    tax year (under 24 if a student: the screener's `student_full_time`, which asks about
    half-time or more). Without one, a filer must be 25 to 64.

    Income is today's, not the tax year's. Earned income is wages and self-employment as
    reported. AGI is all income except the types that are never taxed (SSI, child support,
    gifts, workers' comp, public assistance, veterans' benefits) and Social Security, none
    of whose taxable part is known.

    Members the screener records without a birth month (the Colorado tax-credit apps send
    age alone) are compared by age, and their age is today's rather than at the end of the
    tax year.

    The residency, SSN, tiebreaker, filing-status and prior-disallowance rules have no
    screener field and are not evaluated. Citizenship is enforced by the program's
    ``legal_status_required``.
    """

    program_code = "federal_eitc"

    child_relationships = ("child", "stepChild", "fosterChild", "grandChild", "sisterOrBrother", "stepSisterOrBrother")
    child_age_limit = 19
    student_age_limit = 24
    childless_min_age = 25
    childless_max_age = 64
    max_counted_children = 3

    investment_income_types = ["investment", "rental", "boarder"]
    agi_excluded_income_types = UNTAXED_INCOME_TYPES

    dependencies = ["age", "relationship", "income_amount", "income_frequency", "income_type"]

    def household_eligible(self, e: Eligibility) -> None:
        self._income_eligible(e)

        if self._qualifying_child_count == 0:
            e.condition(any(self._is_childless_filer_age(filer) for filer in self._filers))

    def household_value(self) -> int:
        return self._federal_credit()

    def _income_eligible(self, e: Eligibility) -> None:
        """
        The income rules, which don't depend on a filer's age. A subclass whose route waives the
        age band (NJ's) calls this too, so it can't drift from the federal credit's income rules.
        """
        column = self._column

        e.condition(self._investment_income <= self._params.investment_income_limit)
        e.condition(0 < self._earned_income < column.limit)
        e.condition(self._agi < column.limit)

        # EIC Worksheet A, line 2: a $0 lookup at earned income ends the claim. A $0 reached only
        # through the AGI lookup (line 6) stays eligible, at a value of $0.
        e.condition(eic_table(self._earned_income, column) > 0)

    def _federal_credit(self) -> int:
        column = self._column

        # EIC Worksheet A, lines 5-6: past the phase-out start, the smaller of the two lookups.
        credit = eic_table(self._earned_income, column)
        if self._agi != self._earned_income and self._agi >= column.phase_out_start:
            credit = min(credit, eic_table(self._agi, column))

        return credit

    def member_value(self, member: HouseholdMember) -> int:
        return 0

    @cached_property
    def _params(self) -> EitcYear:
        """
        The tax year's parameters. A year with none yet (a rollover the table wasn't updated
        for) is priced with the latest year we have and reported, rather than raising: an
        exception drops the credit from the results of every white label.
        """
        tax_year = self.tax_year
        if tax_year in EITC_YEARS:
            return EITC_YEARS[tax_year]

        latest = max(EITC_YEARS)
        capture_message(
            f"No federal EITC parameters for tax year {tax_year}; using {latest}.",
            level="error",
        )
        return EITC_YEARS[latest]

    @cached_property
    def _column(self) -> EitcColumn:
        n = min(self._qualifying_child_count, self.max_counted_children)
        return self._params.columns[(n, self._is_joint)]

    @cached_property
    def _is_joint(self) -> bool:
        return self.screen.is_joint()

    @cached_property
    def _filers(self) -> list[HouseholdMember]:
        members = self.screen.household_members.all()
        filers = [m for m in members if m.relationship == "headOfHousehold"]
        if self._is_joint:
            filers += [m for m in members if m.relationship == "spouse"]

        return filers

    def _filer_income(self, types: Collection[str], exclude: Collection[str] = ()) -> float:
        return sum(filer.calc_gross_income("yearly", types, exclude) for filer in self._filers)

    @cached_property
    def _earned_income(self) -> float:
        return self._filer_income(["earned"])

    @cached_property
    def _agi(self) -> float:
        return self._filer_income(["all"], self.agi_excluded_income_types)

    @cached_property
    def _investment_income(self) -> float:
        return self._filer_income(self.investment_income_types)

    @cached_property
    def _qualifying_child_count(self) -> int:
        return sum(
            1
            for member in self.screen.household_members.all()
            if member.relationship in self.child_relationships and self._meets_child_age(member)
        )

    def _meets_child_age(self, member: HouseholdMember) -> bool:
        # A child born after the tax year wasn't alive in it, disabled or not.
        if member.birth_year is not None and member.birth_year > self.tax_year:
            return False

        if member.has_disability():
            return True

        if not any(self._is_younger(member, filer) for filer in self._filers):
            return False

        age = member.age_at_end_of_year(self.tax_year)
        if age is None:
            return False

        if age < self.child_age_limit:
            return True

        return bool(member.student_full_time) and age < self.student_age_limit

    @staticmethod
    def _is_younger(member: HouseholdMember, filer: HouseholdMember) -> bool:
        """
        Born in a later month than the filer. The screener has no day of birth, so a child
        born in the filer's own month doesn't count as younger.
        """
        if member.birth_year_month is not None and filer.birth_year_month is not None:
            return member.birth_year_month > filer.birth_year_month

        member_age, filer_age = member.calc_age(), filer.calc_age()
        return member_age is not None and filer_age is not None and member_age < filer_age

    def _is_childless_filer_age(self, filer: HouseholdMember) -> bool:
        age = filer.age_at_end_of_year(self.tax_year)
        return age is not None and self.childless_min_age <= age <= self.childless_max_age
