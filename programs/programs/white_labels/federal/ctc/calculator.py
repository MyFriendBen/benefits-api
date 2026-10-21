from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from math import ceil
from typing import Optional

from sentry_sdk import capture_message

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import DEPENDENT_ELIGIBLE_RELATIONSHIPS, HouseholdMember

JOINT = "joint"
HEAD_OF_HOUSEHOLD = "head_of_household"
SINGLE = "single"

#: A tax bracket: the taxable income it runs up to (None for the top bracket) and its rate.
Bracket = tuple[Optional[int], Decimal]


@dataclass(frozen=True)
class CtcYear:
    """One tax year's parameters (spec section 7), keyed by filing status where they differ."""

    per_child_credit: int
    other_dependent_credit: int
    phase_out_per_1000: int
    phase_out_threshold: dict[str, int]
    refundable_max: int
    refundable_rate: Decimal
    earned_income_floor: int
    # A relative counts as a dependent only with gross income under this (spec section 4 `odc_dependent`).
    qualifying_relative_income_limit: int
    standard_deduction: dict[str, int]
    # The addition to the standard deduction for each filer 65 or older or blind.
    extra_deduction: dict[str, int]
    senior_age: int
    tax_brackets: dict[str, tuple[Bracket, ...]]


def _brackets(*tops: int) -> tuple[Bracket, ...]:
    """The seven ordinary income brackets from the top of each of the first six (spec section 7, tax)."""
    rates = ("0.10", "0.12", "0.22", "0.24", "0.32", "0.35")
    return tuple((top, Decimal(rate)) for top, rate in zip(tops, rates)) + ((None, Decimal("0.37")),)


# The 2025 tax year's figures, as spec section 7 states them: the credit amounts, phase-out,
# refundable limb, qualifying-relative limit, standard deduction and the ordinary income
# brackets the tax on taxable income is figured from.
CTC_YEARS: dict[int, CtcYear] = {
    2025: CtcYear(
        per_child_credit=2_200,
        other_dependent_credit=500,
        phase_out_per_1000=50,
        phase_out_threshold={JOINT: 400_000, HEAD_OF_HOUSEHOLD: 200_000, SINGLE: 200_000},
        refundable_max=1_700,
        refundable_rate=Decimal("0.15"),
        earned_income_floor=2_500,
        qualifying_relative_income_limit=5_200,
        standard_deduction={JOINT: 31_500, HEAD_OF_HOUSEHOLD: 23_625, SINGLE: 15_750},
        extra_deduction={JOINT: 1_600, HEAD_OF_HOUSEHOLD: 2_000, SINGLE: 2_000},
        senior_age=65,
        tax_brackets={
            JOINT: _brackets(23_850, 96_950, 206_700, 394_600, 501_050, 751_600),
            HEAD_OF_HOUSEHOLD: _brackets(17_000, 64_850, 103_350, 197_300, 250_500, 626_350),
            SINGLE: _brackets(11_925, 48_475, 103_350, 197_300, 250_525, 626_350),
        },
    ),
}

#: Taxable income from which the Tax Computation Worksheet replaces the Tax Table (spec section 7, tax).
TAX_TABLE_CEILING = 100_000


def bracket_tax(amount: Decimal, brackets: tuple[Bracket, ...]) -> Decimal:
    """The tax on ``amount`` from the bracket schedule, to the cent: the Tax Computation Worksheet (spec section 7)."""
    tax = Decimal(0)
    lower = Decimal(0)
    for top, rate in brackets:
        upper = amount if top is None else min(amount, Decimal(top))
        if upper <= lower:
            break
        tax += (upper - lower) * rate
        lower = upper

    return tax


def tax_table_row(amount: Decimal) -> tuple[int, int]:
    """The Tax Table row holding ``amount``: $5, $10, $10, then $25 rows to $3,000 and $50 rows above (spec section 7)."""
    if amount < 5:
        return 0, 5
    if amount < 15:
        return 5, 15
    if amount < 25:
        return 15, 25

    width = 25 if amount < 3_000 else 50
    low = int(amount) // width * width
    return low, low + width


def income_tax(taxable_income: Decimal, brackets: tuple[Bracket, ...]) -> Decimal:
    """
    Federal income tax on ``taxable_income`` before any credits (spec section 7, tax).

    Below $100,000 the Tax Table applies: each row is priced at its midpoint and rounded
    to the dollar, which reproduces the published rows. From $100,000 the Tax Computation
    Worksheet applies the brackets exactly.
    """
    if taxable_income <= 0:
        return Decimal(0)

    if taxable_income < TAX_TABLE_CEILING:
        low, high = tax_table_row(taxable_income)
        return bracket_tax(Decimal(low + high) / 2, brackets).quantize(Decimal(1), rounding=ROUND_HALF_UP)

    return bracket_tax(taxable_income, brackets)


class FederalCtc(ProgramCalculator):
    """
    Federal Child Tax Credit and Credit for Other Dependents, estimated for the program's
    tax year.

    Rules and figures: program-ops `programs/white_labels/federal/ctc/federal_ctc_spec.md`.
    Section references below are to that document.

    The filers are the head and, on a joint return, the member recorded as `spouse`. Every
    other member is claimed when they are the filers' dependent: a qualifying child (a
    child, stepchild, foster child, grandchild or sibling who is younger than a filer or
    permanently disabled, under 19 at the end of the tax year, under 24 if a student, or
    permanently disabled, and whose own income is at most half the household's) or a
    qualifying relative (any relative the screener records whose income, less SSI and cash
    assistance, is under the year's limit). A qualifying child under 17 at the end of the
    tax year earns the child credit; every other dependent earns the credit for other
    dependents. A spouse, partner, roommate or housemate is never a dependent.

    The credit is the per-child and per-dependent amounts, reduced $50 for each $1,000 or
    part of it by which the filers' income exceeds the threshold for their filing status.
    It is then limited to income tax before credits plus the refundable part: 15% of earned
    income over the floor, capped per qualifying child. Income tax is figured on gross
    income less the standard deduction, with the additions for filers 65 or older or blind,
    under the Tax Table or Tax Computation Worksheet; a return files jointly where there is
    a spouse, as head of household where a lone filer claims a dependent, and single
    otherwise. The whole credit is the household's value; members carry none.

    Income is today's, not the tax year's. Earned income is wages and self-employment as
    reported, and modified AGI is every income stream the filers report. Permanently and
    totally disabled is read as the screener's `disabled` and `long_term_disability` both
    ticked. Members recorded without a birth month (the Colorado tax-credit apps send age
    alone, with no disability or student answers) are compared by age, their age is
    today's, and missing answers read as no.

    Residency, SSN, tiebreaker, filing-status and prior-disallowance rules have no screener
    field and are not evaluated. Citizenship is enforced by the program's
    ``legal_status_required``.
    """

    program_code = "federal_ctc"

    child_relationships = ("child", "stepChild", "fosterChild", "grandChild", "sisterOrBrother", "stepSisterOrBrother")
    dependent_relationships = DEPENDENT_ELIGIBLE_RELATIONSHIPS
    ctc_child_age_limit = 17
    child_age_limit = 19
    student_age_limit = 24
    # Welfare income is tax-exempt, so it is left out of a relative's gross income
    # (spec section 5 `odc_relative_gross_income`).
    relative_income_excluded_types = ["sSI", "cashAssistance", "cashAssistanceOther"]

    dependencies = ["age", "relationship", "income_amount", "income_frequency", "income_type"]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        e.condition(member in self._qualifying_children or member in self._other_dependents)

    def household_value(self) -> float:
        # Spec section 7: credit amounts, phase-out, then the cap at tax plus the refundable limb.
        params = self._params
        status = self._filing_status
        children = len(self._qualifying_children)

        credit = Decimal(
            params.per_child_credit * children + params.other_dependent_credit * len(self._other_dependents)
        )
        excess_income = max(self._modified_agi - params.phase_out_threshold[status], Decimal(0))
        credit = max(credit - params.phase_out_per_1000 * ceil(excess_income / 1_000), Decimal(0))

        earned_income_over_floor = max(self._earned_income - params.earned_income_floor, Decimal(0))
        refundable = min(Decimal(params.refundable_max * children), params.refundable_rate * earned_income_over_floor)

        return float(min(credit, self._income_tax + refundable))

    @cached_property
    def _params(self) -> CtcYear:
        """
        The tax year's parameters. A year with none yet (a rollover the table wasn't updated
        for) is priced with the latest year we have and reported, rather than raising: an
        exception from a displayed program fails the whole results page, and this program
        shows in every white label.
        """
        tax_year = self.tax_year
        if tax_year in CTC_YEARS:
            return CTC_YEARS[tax_year]

        latest = max(CTC_YEARS)
        capture_message(
            f"No federal CTC parameters for tax year {tax_year}; using {latest}.",
            level="error",
        )
        return CTC_YEARS[latest]

    @cached_property
    def _is_joint(self) -> bool:
        return self.screen.is_joint()

    @cached_property
    def _filers(self) -> list[HouseholdMember]:
        """The head and, on a joint return, the spouse (spec section 7, filing status)."""
        members = self.screen.household_members.all()
        filers = [m for m in members if m.relationship == "headOfHousehold"]
        if self._is_joint:
            filers += [m for m in members if m.relationship == "spouse"]

        return filers

    @cached_property
    def _filing_status(self) -> str:
        """Joint with a spouse, head of household for a lone filer with a dependent, else single (spec section 7)."""
        if self._is_joint:
            return JOINT
        if self._qualifying_children or self._other_dependents:
            return HEAD_OF_HOUSEHOLD
        return SINGLE

    def _filer_income(self, types: list[str], exclude: Optional[list[str]] = None) -> Decimal:
        return Decimal(str(sum(filer.calc_gross_income("yearly", types, exclude or []) for filer in self._filers)))

    @cached_property
    def _earned_income(self) -> Decimal:
        """Wages and self-employment as reported (spec section 7, earned income)."""
        return self._filer_income(["earned"])

    @cached_property
    def _modified_agi(self) -> Decimal:
        """Every income stream the filers report (spec section 7, modified AGI)."""
        return self._filer_income(["all"])

    @cached_property
    def _income_tax(self) -> Decimal:
        """Tax on gross income less the standard deduction and its 65-or-blind additions (spec section 7, tax)."""
        params = self._params
        status = self._filing_status
        extra_boxes = sum(1 for filer in self._filers if self._is_senior(filer) or bool(filer.visually_impaired))
        deduction = params.standard_deduction[status] + params.extra_deduction[status] * extra_boxes
        taxable_income = max(self._modified_agi - deduction, Decimal(0))

        return income_tax(taxable_income, params.tax_brackets[status])

    @cached_property
    def _dependents(self) -> tuple[list[HouseholdMember], list[HouseholdMember]]:
        """The members the filers claim: (qualifying children for the CTC, other dependents). Spec section 3 routes."""
        children: list[HouseholdMember] = []
        others: list[HouseholdMember] = []
        for member in self.screen.household_members.all():
            if member in self._filers:
                continue
            if self._is_qualifying_child(member):
                (children if self._is_ctc_child(member) else others).append(member)
            elif self._is_qualifying_relative(member):
                others.append(member)

        return children, others

    @property
    def _qualifying_children(self) -> list[HouseholdMember]:
        return self._dependents[0]

    @property
    def _other_dependents(self) -> list[HouseholdMember]:
        return self._dependents[1]

    def _is_qualifying_child(self, member: HouseholdMember) -> bool:
        """A qualifying child: spec section 4 `child_relationship`, `odc_child_age`, `child_younger_than_filer`
        and `child_is_dependent` (the support test by income proxy)."""
        if member.relationship not in self.child_relationships:
            return False

        disabled = self._is_permanently_disabled(member)
        if not disabled and not any(self._is_younger(member, filer) for filer in self._filers):
            return False

        if not disabled:
            age = self._age_at_year_end(member)
            if age is None:
                return False
            if age >= self.child_age_limit and not (bool(member.student) and age < self.student_age_limit):
                return False

        # A child who provides over half their own support is not a qualifying child. The
        # screener collects no support, so a child earning over half the household's income
        # stands in for one.
        return member.calc_gross_income("yearly", ["all"]) <= self.screen.calc_gross_income("yearly", ["all"]) / 2

    def _is_ctc_child(self, member: HouseholdMember) -> bool:
        """A qualifying child who has not reached 17 by the end of the tax year (spec section 4 `child_age`)."""
        age = self._age_at_year_end(member)
        return age is not None and age < self.ctc_child_age_limit

    def _is_qualifying_relative(self, member: HouseholdMember) -> bool:
        """A qualifying relative: any relative whose gross income is under the year's limit (spec section 4 `odc_dependent`)."""
        if member.relationship not in self.dependent_relationships:
            return False

        income = member.calc_gross_income("yearly", ["all"], self.relative_income_excluded_types)
        return income < self._params.qualifying_relative_income_limit

    def _age_at_year_end(self, member: HouseholdMember) -> Optional[int]:
        return member.age_at_end_of_year(self.tax_year)

    def _is_senior(self, filer: HouseholdMember) -> bool:
        """65 or older at the end of the tax year, for the extra standard deduction (spec section 7)."""
        age = self._age_at_year_end(filer)
        return age is not None and age >= self._params.senior_age

    @staticmethod
    def _is_permanently_disabled(member: HouseholdMember) -> bool:
        """The screener's stand-in for permanently and totally disabled (spec section 5 `disability_definition`)."""
        return bool(member.disabled) and bool(member.long_term_disability)

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
