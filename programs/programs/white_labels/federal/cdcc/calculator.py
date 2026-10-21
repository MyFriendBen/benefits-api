from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from math import ceil

from sentry_sdk import capture_message

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import DEPENDENT_ELIGIBLE_RELATIONSHIPS, HouseholdMember


@dataclass(frozen=True)
class CdccYear:
    """
    One tax year's parameters for the credit: the applicable-percentage schedule of
    Form 2441, line 8, and the dollar limits of 26 U.S.C. § 21(c) and (d)(2).

    The schedule starts at ``top_rate`` for AGI up to ``top_rate_limit`` and loses one point
    for each ``first_step`` (or fraction) over it, but never below ``middle_rate``. Past
    ``middle_rate_limit`` it loses one point for each ``second_step`` (or fraction) over that,
    but never below ``floor_rate``. The second reduction is the only place joint and other
    filers differ, so those two are indexed by ``is_joint``: ``(other, joint)``.
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


# Instructions for Form 2441 (2026), draft dated 2026-08-21, Line 8, 2026 Phaseout Schedule;
# limits from 26 U.S.C. § 21(c) and (d)(2).
CDCC_YEARS: dict[int, CdccYear] = {
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
    ),
}


def applicable_percentage(agi: float, is_joint: bool, params: CdccYear) -> int:
    """The credit's percentage of work-related expenses for ``agi``, in whole points."""
    if agi <= params.top_rate_limit:
        return params.top_rate

    middle_rate_limit = params.middle_rate_limit[is_joint]
    if agi <= middle_rate_limit:
        over = ceil(Decimal(str(agi - params.top_rate_limit)) / params.first_step)
        return max(params.top_rate - over, params.middle_rate)

    over = ceil(Decimal(str(agi - middle_rate_limit)) / params.second_step[is_joint])
    return max(params.middle_rate - over, params.floor_rate)


class FederalCdcc(ProgramCalculator):
    """
    Federal Child and Dependent Care Credit (26 U.S.C. § 21), figured as Form 2441 does.

    The filers are the head and, on a joint return, the member recorded as ``spouse``. A
    qualifying individual is a member in a dependent relationship who is under 13 today or
    has a disability flag, or a spouse with a disability flag. The household also needs a
    child care or dependent care expense, and every filer needs earned income (wages or
    self-employment). A spouse who is a full-time student or has a disability flag is
    deemed to earn $250 a month ($500 with two or more qualifying individuals), as
    § 21(d)(2) provides.

    The credit is the applicable percentage for the filers' income times the smallest of
    the care expenses, the dollar limit ($3,000 for one qualifying individual, $6,000 for
    two or more) and the lowest-earning filer's earned income.

    Approximations the screener forces: gross income stands in for adjusted gross income,
    a disability flag stands in for being incapable of self-care, a full-time-student flag
    deems income for all twelve months, every child care or dependent care expense counts
    (kindergarten, overnight camp, a related provider and medical-deduction overlap are not
    asked), employer dependent care benefits do not reduce the limit, and the credit is not
    capped at the tax owed. Ages are today's, not the tax year's.

    A missing disability or student answer reads as false rather than dropping the program,
    so the Colorado tax-credit apps' age-only screens still see the credit.
    """

    program_code = "federal_cdcc"

    qualifying_child_age_limit = 13
    care_expense_types = ("childCare", "dependentCare")

    dependencies = [
        "age",
        "relationship",
        "income_amount",
        "income_frequency",
        "income_type",
        "expense_type",
        "expense_amount",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        e.condition(self._is_qualifying_individual(e.member))

    def household_eligible(self, e: Eligibility) -> None:
        e.condition(len(self._filers) > 0)
        e.condition(self._care_expenses > 0)
        e.condition(all(self._earned_income(filer) > 0 for filer in self._filers))

    def household_value(self) -> int:
        params = self._params
        percentage = applicable_percentage(self._agi, self._is_joint, params)
        expense_limit = params.expense_limit[self._has_two_or_more_qualifying]
        lowest_earned_income = min(self._earned_income(filer) for filer in self._filers)

        base = min(self._care_expenses, expense_limit, lowest_earned_income)
        credit = Decimal(percentage) * Decimal(str(base)) / 100

        return int(credit.quantize(Decimal(1), rounding=ROUND_HALF_UP))

    def member_value(self, member: HouseholdMember) -> int:
        return 0

    @cached_property
    def _params(self) -> CdccYear:
        """
        The tax year's parameters. A year with none yet (a rollover the table wasn't updated
        for) is priced with the latest year we have and reported, rather than raising: an
        exception from a displayed program fails the whole results page, and this program
        shows in every white label.
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
    def _agi(self) -> float:
        return sum(filer.calc_gross_income("yearly", ["all"]) for filer in self._filers)

    @cached_property
    def _care_expenses(self) -> float:
        return self.screen.calc_expenses("yearly", list(self.care_expense_types))

    @cached_property
    def _qualifying_count(self) -> int:
        return sum(1 for member in self.screen.household_members.all() if self._is_qualifying_individual(member))

    @property
    def _has_two_or_more_qualifying(self) -> bool:
        return self._qualifying_count >= 2

    def _is_qualifying_individual(self, member: HouseholdMember) -> bool:
        if member.relationship == "spouse":
            return bool(member.has_disability())

        if member.relationship not in DEPENDENT_ELIGIBLE_RELATIONSHIPS:
            return False

        if member.has_disability():
            return True

        age = member.calc_age()
        return age is not None and age < self.qualifying_child_age_limit

    def _earned_income(self, filer: HouseholdMember) -> float:
        """
        A filer's yearly earned income. A spouse who is a full-time student or has a
        disability flag earns at least the deemed amount for all twelve months.
        """
        earned = filer.calc_gross_income("yearly", ["earned"])

        if filer.relationship == "spouse" and (filer.student_full_time or filer.has_disability()):
            deemed = self._params.deemed_spouse_monthly_income[self._has_two_or_more_qualifying] * 12
            return max(earned, float(deemed))

        return earned
