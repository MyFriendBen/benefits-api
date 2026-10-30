"""Federal Child and Dependent Care Credit.

Rules and figures: program-ops `programs/white_labels/federal/cdcc/federal_cdcc_spec.md`.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from math import ceil
from typing import Optional

from sentry_sdk import capture_message

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.white_labels.federal.tax import (
    FEDERAL_TAX_YEARS,
    HEAD_OF_HOUSEHOLD,
    JOINT,
    UNTAXED_INCOME_TYPES,
    FederalTaxYear,
    tax_owed,
)
from screener.models import DEPENDENT_ELIGIBLE_RELATIONSHIPS, HouseholdMember


@dataclass(frozen=True)
class CdccYear:
    """
    One tax year's parameters (spec section 7 Benefit Value; deemed spouse income from
    section 4 `earned_income`). The percentage steps down from ``top_rate`` to ``middle_rate``
    and then to ``floor_rate``; joint and other filers differ only in the second step, so
    those two fields are indexed ``(other, joint)``.
    """

    top_rate: int
    middle_rate: int
    floor_rate: int
    top_rate_limit: int
    first_step: int
    middle_rate_limit: tuple[int, int]
    second_step: tuple[int, int]
    # Indexed by whether the household has two or more qualifying individuals.
    expense_limit: tuple[int, int]
    # Monthly earned income a student or disabled spouse is deemed to have, same indexing.
    deemed_spouse_monthly_income: tuple[int, int]
    # Spec section 7, the tax owed and its terms.
    tax: FederalTaxYear


# Percentage schedule, dollar limits and tax, spec section 7; deemed spouse income, spec section 4 `earned_income`.
CDCC_YEARS: dict[int, CdccYear] = {
    # One reduction only: 35% down to 20% above $43,000, for every filer.
    2025: CdccYear(
        top_rate=35,
        middle_rate=20,
        floor_rate=20,
        top_rate_limit=15_000,
        first_step=2_000,
        middle_rate_limit=(43_000, 43_000),
        second_step=(2_000, 2_000),
        expense_limit=(3_000, 6_000),
        deemed_spouse_monthly_income=(250, 500),
        tax=FEDERAL_TAX_YEARS[2025],
    ),
    2026: CdccYear(
        top_rate=50,
        middle_rate=35,
        floor_rate=20,
        top_rate_limit=15_000,
        first_step=2_000,
        middle_rate_limit=(75_000, 150_000),
        second_step=(2_000, 4_000),
        expense_limit=(3_000, 6_000),
        deemed_spouse_monthly_income=(250, 500),
        tax=FEDERAL_TAX_YEARS[2026],
    ),
}


def applicable_percentage(agi: Decimal, is_joint: bool, params: CdccYear) -> int:
    """The applicable percentage for ``agi``, in whole points (spec section 7 table)."""
    if agi <= params.top_rate_limit:
        return params.top_rate

    middle_rate_limit = params.middle_rate_limit[is_joint]
    if agi <= middle_rate_limit:
        over = ceil((agi - params.top_rate_limit) / params.first_step)
        return max(params.top_rate - over, params.middle_rate)

    over = ceil((agi - middle_rate_limit) / params.second_step[is_joint])
    return max(params.middle_rate - over, params.floor_rate)


class FederalCdcc(ProgramCalculator):
    """
    Federal Child and Dependent Care Credit; rules and figures are in the spec named above.

    Screener mapping: filers are the head and, on a joint return, the ``spouse`` member; a
    qualifying individual is a ``DEPENDENT_ELIGIBLE_RELATIONSHIPS`` member under the age limit
    today or with any disability flag, or, on a joint return, a filer with one; care expenses are the
    ``childCare`` and ``dependentCare`` types; earned income is the ``earned`` income group.
    Deviations: filers' income less the untaxed types stands in for AGI; a disability flag
    for incapable of self-care; deemed income runs all twelve months, for one filer; tax owed
    is the Tax Table below $100,000 and the brackets above, after the standard deduction,
    filing jointly with a ``spouse`` member and as head of household otherwise; ages are today's.
    Residency, custody, provider, schooling and employer-benefit rules are not evaluated.
    Missing disability or student answers read as no, so age-only screens still see the credit.
    """

    program_code = "federal_cdcc"

    qualifying_child_age_limit = 13
    care_expense_types = ("childCare", "dependentCare")
    # Spec section 7 `agi`.
    tax_exempt_income_types = UNTAXED_INCOME_TYPES

    dependencies = [
        "age",
        "relationship",
        "income_amount",
        "income_frequency",
        "income_type",
        "expense_type",
        "expense_amount",
        "expense_frequency",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        # spec section 4 `qualifying_individual`
        e.condition(self._is_qualifying_individual(e.member))

    def household_eligible(self, e: Eligibility) -> None:
        e.condition(len(self._filers) > 0)
        # spec section 4 `work_related_care_expenses`
        e.condition(self._care_expenses > 0)
        # spec section 4 `earned_income`
        e.condition(all(self._earned_income(filer) > 0 for filer in self._filers))
        # spec section 4 `tax_liability`
        e.condition(self._income_tax > 0)

    def household_value(self) -> int:
        """Spec section 7 Benefit Value, carried on the household; members carry no value."""
        params = self._params
        percentage = applicable_percentage(self._agi, self._is_joint, params)
        expense_limit = params.expense_limit[self._has_two_or_more_qualifying]
        lowest_earned_income = min(self._earned_income(filer) for filer in self._filers)

        base = min(self._care_expenses, expense_limit, lowest_earned_income)
        credit = min(Decimal(percentage) * Decimal(str(base)) / 100, self._income_tax)

        return int(credit.quantize(Decimal(1), rounding=ROUND_HALF_UP))

    def member_value(self, member: HouseholdMember) -> int:
        return 0

    @cached_property
    def _params(self) -> CdccYear:
        """
        The tax year's parameters. A year with none yet is priced with the latest year and
        reported to Sentry rather than raising: an exception would drop the credit from every
        white label's results.
        """
        tax_year = self.tax_year
        if tax_year in CDCC_YEARS:
            return CDCC_YEARS[tax_year]

        latest = max(CDCC_YEARS)
        capture_message(
            f"No federal CDCC parameters for tax year {tax_year}; using {latest}.",
            level="error",
        )
        return CDCC_YEARS[latest]

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

    @cached_property
    def _agi(self) -> Decimal:
        return sum(
            (
                Decimal(str(filer.calc_gross_income("yearly", ["all"], self.tax_exempt_income_types)))
                for filer in self._filers
            ),
            Decimal(0),
        )

    @cached_property
    def _income_tax(self) -> Decimal:
        """Spec section 7 `tax_2026`."""
        status = JOINT if self._is_joint else HEAD_OF_HOUSEHOLD
        age_or_blind_count = sum(
            int(self._is_senior(filer)) + int(bool(filer.visually_impaired)) for filer in self._filers
        )
        return tax_owed(self._agi, status, age_or_blind_count, self._params.tax)

    def _is_senior(self, filer: HouseholdMember) -> bool:
        age = filer.calc_age()
        return age is not None and age >= self._params.tax.senior_age

    @cached_property
    def _care_expenses(self) -> float:
        return self.screen.calc_expenses("yearly", list(self.care_expense_types))

    @cached_property
    def _qualifying_count(self) -> int:
        return sum(1 for member in self.screen.household_members.all() if self._is_qualifying_individual(member))

    @cached_property
    def _has_two_or_more_qualifying(self) -> bool:
        return self._qualifying_count >= 2

    def _is_qualifying_individual(self, member: HouseholdMember) -> bool:
        """Spec section 4 `qualifying_individual`. On a joint return either filer is the
        other's spouse, whichever the screener recorded as head."""
        # Born after the tax year: not part of that year's household.
        if member.birth_year_month is not None and member.birth_year_month.year > self.tax_year:
            return False

        if member.relationship == "spouse" or (member.relationship == "headOfHousehold" and self._is_joint):
            return bool(member.has_disability())

        if member.relationship not in DEPENDENT_ELIGIBLE_RELATIONSHIPS:
            return False

        if member.has_disability():
            return True

        age = member.calc_age()
        return age is not None and age < self.qualifying_child_age_limit

    @cached_property
    def _deemed_filer(self) -> Optional[HouseholdMember]:
        """
        Spec section 4 `earned_income`: on a joint return, the one filer deemed to have earned
        income, a student or disabled one, and the lower earner where both are.
        """
        if not self._is_joint:
            return None

        candidates = [filer for filer in self._filers if filer.student_full_time or filer.has_disability()]
        if not candidates:
            return None

        return min(candidates, key=lambda filer: filer.calc_gross_income("yearly", ["earned"]))

    def _earned_income(self, filer: HouseholdMember) -> float:
        """Spec section 4 `earned_income`; the deemed amount is a floor, not an addition."""
        earned = filer.calc_gross_income("yearly", ["earned"])

        if filer == self._deemed_filer:
            deemed = self._params.deemed_spouse_monthly_income[self._has_two_or_more_qualifying] * 12
            return max(earned, float(deemed))

        return earned
