"""ACA Premium Tax Credit — MFB federal base."""

from dataclasses import dataclass
from functools import cached_property
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import ClassVar, Optional

from sentry_sdk import capture_message

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember

#: Open enrollment for the coming year starts November 1, so a screening on or after it is for
#: next year's coverage.
OPEN_ENROLLMENT_START = (11, 1)

#: The screener's taxable income types. `childSupport`, `gifts`, `cashAssistance`,
#: `cashAssistanceOther`, `sSI`, `workersComp` and `veteran` are not taxable; `alimony` is left
#: out (the spec's `agi_adjustments` gap).
TAXABLE_INCOME_TYPES = (
    "wages",
    "selfEmployment",
    "rental",
    "boarder",
    "pension",
    "deferredComp",
    "investment",
    "unemployment",
    "sSRetirement",
    "sSDisability",
    "sSSurvivor",
    "sSDependent",
)
EARNED_INCOME_TYPES = ("wages", "selfEmployment")
SOCIAL_SECURITY_TYPES = ("sSRetirement", "sSDisability", "sSSurvivor", "sSDependent")
#: Social Security that, from the month a member turns 65, stands in for free Medicare Part A.
SOCIAL_SECURITY_RETIREMENT_TYPES = ("sSRetirement", "sSSurvivor", "sSDependent")

GOVERNMENT_COVERAGE_TYPES = ("medicaid", "medicare", "chp", "ma_mass_health", "va")
EMPLOYER_COVERAGE_TYPES = ("employer",)

MONTHS = range(1, 13)


@dataclass(frozen=True)
class ApplicableBand:
    """One row of the applicable percentage table, in percent."""

    #: The row holds `start <= fpl_percent < end`; the last row also holds `fpl_percent == end`.
    start: int
    end: int
    initial: Decimal
    final: Decimal


def _band(start: int, end: int, initial: str, final: str) -> ApplicableBand:
    return ApplicableBand(start, end, Decimal(initial), Decimal(final))


#: Rev. Proc. 2025-25 §3.01 (2026) and Rev. Proc. 2026-26 §3.01 (2027), keyed by coverage year.
APPLICABLE_PERCENTAGE_TABLES: dict[int, tuple[ApplicableBand, ...]] = {
    2026: (
        _band(0, 133, "2.10", "2.10"),
        _band(133, 150, "3.14", "4.19"),
        _band(150, 200, "4.19", "6.60"),
        _band(200, 250, "6.60", "8.44"),
        _band(250, 300, "8.44", "9.96"),
        _band(300, 400, "9.96", "9.96"),
    ),
    2027: (
        _band(0, 133, "2.15", "2.15"),
        _band(133, 150, "3.23", "4.3"),
        _band(150, 200, "4.3", "6.78"),
        _band(200, 250, "6.78", "8.66"),
        _band(250, 300, "8.66", "10.22"),
        _band(300, 400, "10.22", "10.22"),
    ),
}


@dataclass(frozen=True)
class DependentFilingFigures:
    """One tax year's amounts for when a single dependent must file (26 U.S.C. 6012(a)(1))."""

    #: The tax year these amounts are for.
    tax_year: int
    #: The least a dependent's standard deduction can be.
    floor: int
    #: Added to earned income for a dependent's standard deduction.
    addon: int
    #: The basic standard deduction for an unmarried filer.
    basic: int
    #: The additional standard deduction for an unmarried filer who is 65 or older, or blind.
    additional: int


#: Rev. Proc. 2026-35 §3.15. Replace with the next Rev. Proc.'s amounts when the coverage year
#: rolls over; until then a screen for another coverage year is reported to Sentry.
DEPENDENT_FILING = DependentFilingFigures(tax_year=2027, floor=1_400, addon=500, basic=16_600, additional=2_100)
DEPENDENT_SELF_EMPLOYMENT_THRESHOLD = 400
#: Social Security enters a dependent's gross income only where half of it plus their other
#: income exceeds this.
DEPENDENT_SOCIAL_SECURITY_BASE = 25_000

MEDICARE_AGE = 65


def _dollars(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class MfbAca(ProgramCalculator, abstract=True):
    """
    ACA Premium Tax Credit, computed in our own code. Rules: program-ops
    ``programs/cross_white_label/aca/base/aca_base_spec.md``.

    It sits beside the PolicyEngine ``Aca`` in ``base.py``, which the states that haven't had
    their own discovery run still use. Only a state with a program-ops spec subclasses this.

    A household qualifies when its income is 100–400% of the poverty line and at least one
    member of the tax family is in the coverage family: no Medicaid, CHIP, Medicare or VA
    coverage reported, no Social Security disability income, no Social Security retirement
    income from the month they turn 65, not eligible for a program in
    ``medicaid_chip_program_codes``, and no job-based plan. Immigration status is enforced by
    the program row's ``legal_status_required``, not here.

    The credit follows the Form 8962 procedure: the benchmark premium for the coverage family
    less the household's expected contribution, over the full year when nothing changes
    month to month, otherwise month by month.

    Data gaps (spec §5), not evaluated: joint filing, Marketplace enrollment, premium payment,
    incarceration, TRICARE, the Medicare waiting period, employer-offer affordability, coverage
    by month, the under-100% estimate exception, and MAGI adjustments. A domestic partner is
    not a spouse, so they and their income are left out.

    Each state sets:

    - ``program_code``
    - ``medicaid_chip_program_codes``: its full-benefit Medicaid and CHIP program codes, also
      declared in ``gates_on``
    - ``state_taxable_income_types``: any state-only income type that is taxable
    - ``benchmark_premium()``: the second-lowest-cost silver plan's monthly premium for a set of
      members
    """

    medicaid_chip_program_codes: ClassVar[tuple[str, ...]] = ()
    state_taxable_income_types: ClassVar[tuple[str, ...]] = ()

    lower_fpl_multiple = Decimal("1.00")
    upper_fpl_multiple = Decimal("4.00")

    dependencies = (
        "age",
        "relationship",
        "student",
        "visually_impaired",
        "disabled",
        "long_term_disability",
        "insurance",
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def benchmark_premium(self, members: list[HouseholdMember]) -> Decimal:
        """The second-lowest-cost silver plan's monthly premium for ``members``, unrounded."""
        raise NotImplementedError

    # --- the coverage year and the family ---------------------------------------------

    def coverage_year(self) -> int:
        """Next year from November 1, when open enrollment for it starts; this year before."""
        today = self.screen.get_reference_date()
        if (today.month, today.day) >= OPEN_ENROLLMENT_START:
            return today.year + 1

        return today.year

    def tax_family(self) -> list[HouseholdMember]:
        """The head, the member whose relationship is ``spouse``, and every dependent."""
        return self._tax_family

    @cached_property
    def _tax_family(self) -> list[HouseholdMember]:
        return [
            member
            for member in self.screen.household_members.all()
            if member.is_head() or member.relationship == "spouse" or member.is_dependent()
        ]

    def taxable_income_types(self) -> tuple[str, ...]:
        return (*TAXABLE_INCOME_TYPES, *self.state_taxable_income_types)

    # --- income_fpl_band ----------------------------------------------------------------

    def household_income(self) -> Decimal:
        """The head's and spouse's taxable income, plus each dependent's who must file."""
        taxable = self.taxable_income_types()
        income = Decimal(0)
        for member in self.tax_family():
            if member.is_head() or member.relationship == "spouse" or self.dependent_must_file(member):
                income += Decimal(str(member.calc_gross_income("yearly", taxable)))

        return income

    def dependent_must_file(self, member: HouseholdMember) -> bool:
        """
        Whether a dependent's income is high enough that they must file a return, by 26 U.S.C.
        6012(a)(1) at ``DEPENDENT_FILING``'s amounts: gross income at least the basic standard
        deduction (plus the additional amount from 65), unearned income over the floor, or gross
        income over the dependent's standard deduction.
        """
        self_employment = member.calc_gross_income("yearly", ["selfEmployment"])
        if self_employment >= DEPENDENT_SELF_EMPLOYMENT_THRESHOLD:
            return True

        earned = member.calc_gross_income("yearly", EARNED_INCOME_TYPES)
        social_security = member.calc_gross_income("yearly", SOCIAL_SECURITY_TYPES)
        other = member.calc_gross_income("yearly", self.taxable_income_types()) - social_security
        unearned = other - earned
        if social_security / 2 + other > DEPENDENT_SOCIAL_SECURITY_BASE:
            unearned += social_security

        figures = self._dependent_filing_figures()
        age = member.age_at_end_of_year(self.coverage_year())
        aged = age is not None and age >= MEDICARE_AGE
        blind = bool(member.visually_impaired)

        # One additional amount each for 65 or older and for blindness; only age raises the
        # gross income threshold.
        extra = figures.additional * (int(aged) + int(blind))
        gross = earned + unearned
        gross_threshold = figures.basic + (figures.additional if aged else 0)
        dependent_deduction = min(max(figures.floor, earned + figures.addon), figures.basic) + extra

        return gross >= gross_threshold or unearned > figures.floor + extra or gross > dependent_deduction

    def _dependent_filing_figures(self) -> DependentFilingFigures:
        """The current dependent filing amounts, reported when they aren't the coverage year's."""
        year = self.coverage_year()
        if year != DEPENDENT_FILING.tax_year:
            capture_message(
                f"ACA reads the {DEPENDENT_FILING.tax_year} dependent filing amounts for coverage year {year}.",
                level="warning",
            )

        return DEPENDENT_FILING

    def poverty_line(self) -> int:
        """
        The guideline in effect when open enrollment for the coverage year opened: the prior
        year's. ``program.year`` carries it; a row on another edition is reported, not raised.
        """
        year = self.program.year
        expected = self.coverage_year() - 1
        if int(year.period) != expected:
            capture_message(
                f"{self.program_code} reads the {year.period} poverty guideline for coverage year "
                f"{self.coverage_year()}, which uses the {expected} guideline.",
                level="warning",
            )

        return year.get_limit(len(self.tax_family()))

    def household_eligible(self, e: Eligibility) -> None:
        income = self.household_income()
        fpl = Decimal(self.poverty_line())
        e.condition(
            self.lower_fpl_multiple * fpl <= income <= self.upper_fpl_multiple * fpl,
            messages.income_range(income, self.lower_fpl_multiple * fpl, self.upper_fpl_multiple * fpl),
        )

    # --- the coverage family ------------------------------------------------------------

    def member_eligible(self, e: MemberEligibility) -> None:
        """In the coverage family for at least one month of the coverage year."""
        member = e.member
        e.condition(member in self.tax_family())
        e.condition(self.no_government_coverage(member))
        e.condition(not member.has_insurance_types(EMPLOYER_COVERAGE_TYPES))

    def turns_65_month(self, member: HouseholdMember) -> Optional[int]:
        """
        The month of the coverage year a member turns 65: 1 for anyone already older, None
        for anyone younger. Without a birth month, a member 65 or older counts as 1.
        """
        if member.birth_year_month is None:
            age = member.calc_age()
            return 1 if age is not None and age >= MEDICARE_AGE else None

        age_this_year = self.coverage_year() - member.birth_year
        if age_this_year > MEDICARE_AGE:
            return 1
        if age_this_year == MEDICARE_AGE:
            return member.birth_month

        return None

    def _draws_retirement_social_security(self, member: HouseholdMember) -> bool:
        return member.calc_gross_income("yearly", SOCIAL_SECURITY_RETIREMENT_TYPES) > 0

    def no_government_coverage(self, member: HouseholdMember) -> bool:
        if member.has_insurance_types(GOVERNMENT_COVERAGE_TYPES):
            return False

        if member.calc_gross_income("yearly", ["sSDisability"]) > 0:
            return False

        if self.turns_65_month(member) == 1 and self._draws_retirement_social_security(member):
            return False

        for code in self.medicaid_chip_program_codes:
            if self.member_program_eligible(code, member):
                return False

        return True

    def months_in_coverage_family(self, member: HouseholdMember) -> range:
        """
        Every month, except that a member who turns 65 during the year and draws Social
        Security retirement, survivor or spousal income leaves from that month.
        """
        month = self.turns_65_month(member)
        if month is not None and self._draws_retirement_social_security(member):
            return range(1, month)

        return MONTHS

    # --- the credit ---------------------------------------------------------------------

    def applicable_percentage(self, fpl_percent: int) -> Decimal:
        """The share of income the household is expected to pay, in percent, to 0.01%."""
        table = self._applicable_percentage_table()
        for band in table:
            in_band = band.start <= fpl_percent < band.end or (band is table[-1] and fpl_percent == band.end)
            if not in_band:
                continue

            if band.initial == band.final:
                return band.initial

            slope = (band.final - band.initial) * (fpl_percent - band.start) / (band.end - band.start)
            return (band.initial + slope).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        raise ValueError(f"{fpl_percent}% of the poverty line is outside the applicable percentage table")

    def _applicable_percentage_table(self) -> tuple[ApplicableBand, ...]:
        year = self.coverage_year()
        if year in APPLICABLE_PERCENTAGE_TABLES:
            return APPLICABLE_PERCENTAGE_TABLES[year]

        latest = max(APPLICABLE_PERCENTAGE_TABLES)
        capture_message(
            f"No ACA applicable percentage table for coverage year {year}; using {latest}.",
            level="warning",
        )
        return APPLICABLE_PERCENTAGE_TABLES[latest]

    def value(self, e: Eligibility) -> None:
        if not e.eligible:
            return

        family = [member_e.member for member_e in e.eligible_members if member_e.eligible]
        e.household_value = int(self.annual_credit(family))

    def annual_credit(self, coverage_family: list[HouseholdMember]) -> Decimal:
        """Form 8962: the full-year path where nothing changes month to month, else monthly."""
        income = self.household_income()
        fpl = Decimal(self.poverty_line())
        fpl_percent = int((income / fpl * 100).to_integral_value(rounding=ROUND_DOWN))
        annual_contribution = _dollars(income * self.applicable_percentage(fpl_percent) / 100)

        months = {member.id: self.months_in_coverage_family(member) for member in coverage_family}
        monthly_families = [[member for member in coverage_family if month in months[member.id]] for month in MONTHS]

        if all(len(family) == len(coverage_family) for family in monthly_families):
            annual_benchmark = _dollars(self.benchmark_premium(coverage_family) * 12)
            return max(Decimal(0), annual_benchmark - annual_contribution)

        monthly_contribution = _dollars(annual_contribution / 12)
        credit = Decimal(0)
        for family in monthly_families:
            if not family:
                continue
            credit += max(Decimal(0), _dollars(self.benchmark_premium(family)) - monthly_contribution)

        return credit
