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
    """One tax year's figures (spec section 7), keyed by filing status where they differ."""

    per_child_credit: int
    other_dependent_credit: int
    phase_out_per_1000: int
    phase_out_threshold: dict[str, int]
    refundable_max: int
    refundable_rate: Decimal
    earned_income_floor: int
    # Spec section 4 `odc_dependent`.
    qualifying_relative_income_limit: int
    standard_deduction: dict[str, int]
    # Spec section 7, standard deduction additions.
    extra_deduction: dict[str, int]
    senior_age: int
    tax_brackets: dict[str, tuple[Bracket, ...]]


def _brackets(*tops: int) -> tuple[Bracket, ...]:
    """The bracket schedule from the tops of all but the last bracket (spec section 7, tax)."""
    rates = ("0.10", "0.12", "0.22", "0.24", "0.32", "0.35")
    return tuple((top, Decimal(rate)) for top, rate in zip(tops, rates)) + ((None, Decimal("0.37")),)


# Each tax year's figures, as spec section 7 states them.
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
    """Tax from the bracket schedule to the cent, as the Tax Computation Worksheet figures it (spec section 7)."""
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
    """The Tax Table row holding ``amount`` (spec section 7, tax)."""
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
    """Income tax before credits: Tax Table rows priced at their midpoint below the ceiling, the
    brackets exactly above it (spec section 7, tax)."""
    if taxable_income <= 0:
        return Decimal(0)

    if taxable_income < TAX_TABLE_CEILING:
        low, high = tax_table_row(taxable_income)
        return bracket_tax(Decimal(low + high) / 2, brackets).quantize(Decimal(1), rounding=ROUND_HALF_UP)

    return bracket_tax(taxable_income, brackets)


class FederalCtc(ProgramCalculator):
    """
    Federal Child Tax Credit and Credit for Other Dependents for the program's tax year.
    Rules and figures: program-ops `programs/white_labels/federal/ctc/federal_ctc_spec.md`;
    section references below are to it.

    Stand-ins: filers are the head plus a member recorded as `spouse` (joint return); any
    relative the screener records can be a dependent, a spouse, partner or roommate never;
    `disabled` + `long_term_disability` stands in for permanently and totally disabled, the
    alternative to the younger-than-filer and age tests; `student` (half-time college enrolment)
    stands in for the student test. Deviations: income is today's, not the
    tax year's; the never-taxed types and, by approximation, every Social Security type are
    left out of income (section 7); a child's support test compares their countable income
    with the rest of the household's. Age-only members (the Colorado tax-credit apps) are
    compared by age, their reported age standing for age at the tax year's end, with missing
    answers read as no. The
    credit is the household's value; a missing parameter year falls back to the latest and
    reports to Sentry. Residency, SSN, tiebreaker, filing-status and prior-disallowance
    rules are not evaluated; citizenship is enforced by ``legal_status_required``.
    """

    program_code = "federal_ctc"

    child_relationships = ("child", "stepChild", "fosterChild", "grandChild", "sisterOrBrother", "stepSisterOrBrother")
    dependent_relationships = DEPENDENT_ELIGIBLE_RELATIONSHIPS
    ctc_child_age_limit = 17
    child_age_limit = 19
    student_age_limit = 24
    # The never-taxed types, plus every Social Security type by approximation (spec section 7):
    # left out of the filers' income and of a relative's gross income (section 5
    # `odc_relative_gross_income`). Where the approximation misses, the estimated tax cap is
    # lower, never the credit higher.
    tax_exempt_income_types = [
        "sSI",
        "cashAssistance",
        "cashAssistanceOther",
        "childSupport",
        "gifts",
        "workersComp",
        "veteran",
        "sSDisability",
        "sSSurvivor",
        "sSRetirement",
        "sSDependent",
    ]

    dependencies = ["age", "relationship", "income_amount", "income_frequency", "income_type"]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        e.condition(member in self._qualifying_children or member in self._other_dependents)

    def household_value(self) -> float:
        # Spec section 7.
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
        """The tax year's figures; a year with none is priced with the latest and reported to
        Sentry rather than raising, since an exception here fails every white label's results page."""
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
        # The literal `spouse` relationship, on purpose: `is_spouse()` and `relationship_map()`
        # treat `domesticPartner` as spouse-equivalent, but for federal tax a domestic partner
        # is neither a filer nor a dependent.
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
        """Spec section 7, filing status."""
        if self._is_joint:
            return JOINT
        if self._qualifying_children or self._other_dependents:
            return HEAD_OF_HOUSEHOLD
        return SINGLE

    def _filer_income(self, types: list[str], exclude: Optional[list[str]] = None) -> Decimal:
        return sum(
            (Decimal(str(filer.calc_gross_income("yearly", types, exclude or []))) for filer in self._filers),
            Decimal(0),
        )

    @cached_property
    def _earned_income(self) -> Decimal:
        """The screener's earned types as reported (spec section 7, earned income)."""
        return self._filer_income(["earned"])

    @cached_property
    def _modified_agi(self) -> Decimal:
        """Every taxable income stream the filers report (spec section 7, modified AGI)."""
        return self._filer_income(["all"], self.tax_exempt_income_types)

    @cached_property
    def _income_tax(self) -> Decimal:
        """Spec section 7, tax."""
        params = self._params
        status = self._filing_status
        extra_boxes = sum(int(self._is_senior(filer)) + int(bool(filer.visually_impaired)) for filer in self._filers)
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
        """Spec section 4 `child_relationship`, `child_is_dependent`, and `child_younger_than_filer` /
        `odc_child_age` or their `disability_definition` alternative."""
        if member.relationship not in self.child_relationships:
            return False

        age = self._age_at_year_end(member)
        if age is None:
            return False

        disabled = self._is_permanently_disabled(member)
        if not disabled and not any(self._is_younger(member, filer) for filer in self._filers):
            return False
        if not disabled and age >= self.child_age_limit and not (bool(member.student) and age < self.student_age_limit):
            return False

        # The support test by proxy: the child's countable income against the rest of the
        # household's combined countable income.
        others = sum(
            (self._countable_income(other) for other in self.screen.household_members.all() if other.pk != member.pk),
            Decimal(0),
        )
        return self._countable_income(member) <= others

    def _countable_income(self, member: HouseholdMember) -> Decimal:
        """Yearly income less the types treated as untaxed."""
        return Decimal(str(member.calc_gross_income("yearly", ["all"], self.tax_exempt_income_types)))

    def _is_ctc_child(self, member: HouseholdMember) -> bool:
        """Spec section 4 `child_age`."""
        age = self._age_at_year_end(member)
        return age is not None and age < self.ctc_child_age_limit

    def _is_qualifying_relative(self, member: HouseholdMember) -> bool:
        """Spec section 4 `odc_dependent`."""
        if member.relationship not in self.dependent_relationships:
            return False

        return self._countable_income(member) < self._params.qualifying_relative_income_limit

    def _age_at_year_end(self, member: HouseholdMember) -> Optional[int]:
        """Age at the tax year's end; a member with an age but no birth month is taken at the age
        reported, which reads a year high for anyone with a birthday since year end."""
        if member.birth_year_month is not None:
            return member.age_at_end_of_year(self.tax_year)

        return member.calc_age()

    def _is_senior(self, filer: HouseholdMember) -> bool:
        """Spec section 7, standard deduction addition for age."""
        age = self._age_at_year_end(filer)
        return age is not None and age >= self._params.senior_age

    @staticmethod
    def _is_permanently_disabled(member: HouseholdMember) -> bool:
        """The screener's stand-in for permanently and totally disabled (spec section 4 `disability_definition`)."""
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
