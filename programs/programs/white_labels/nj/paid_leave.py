"""
The rules New Jersey's Temporary Disability Insurance (TDI) and Family Leave Insurance (FLI)
share. Both are paid from one contribution base under the Temporary Disability Benefits Law,
so they have the same earnings test and working-route rate. Each also has an unemployment
route (Disability During Unemployment, Family Leave During Unemployment), paid at the
claimant's unemployment rate.

Routes, judged per member from current income because the screener collects no wage history:

- working: current yearly wages meet the base-year earnings test;
- unemployed: unemployment income and no wages.

Both programs turn away a member reporting SSDI income. The value is a lump sum: a weekly rate
times the average days paid per claim.
"""

from dataclasses import dataclass
from functools import cached_property
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Optional

from sentry_sdk import capture_message

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember


@dataclass(frozen=True)
class PaidLeaveYear:
    """One calendar year's figures, which NJ Labor resets every January 1."""

    # Base-year earnings test: 1,000 times the NJ minimum wage.
    earnings_test: int
    # Weekly maximum for TDI and FLI on the working route.
    max_weekly_rate: int
    # Weekly maximum for Family Leave During Unemployment.
    fldu_max_weekly_rate: int


# Each claim year's figures, as the TDI and FLI specs state them.
PAID_LEAVE_YEARS: dict[int, PaidLeaveYear] = {
    2026: PaidLeaveYear(earnings_test=15_500, max_weekly_rate=1_119, fldu_max_weekly_rate=905),
}

BENEFIT_RATE = Decimal("0.85")
WEEKS_PER_YEAR = 52
DAYS_PER_WEEK = 7


class NjPaidLeave(ProgramCalculator, abstract=True):
    """Shared routes, SSDI bar and lump-sum value for NJ TDI and FLI."""

    def unemployment_max_weekly_rate(self) -> Optional[int]:
        """Weekly maximum on the unemployment route, or None for no cap."""
        return None

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        e.condition(self.on_working_route(member) or self.on_unemployment_route(member))
        e.condition(self._income(member, "sSDisability") <= 0)

    def on_working_route(self, member: HouseholdMember) -> bool:
        """Current wages stand in for a covered job and the base-year earnings test."""
        return self._income(member, "wages") >= self.figures.earnings_test

    def on_unemployment_route(self, member: HouseholdMember) -> bool:
        """Collecting unemployment, with no wages, stands in for a UI-eligible claimant out of work."""
        return self._income(member, "unemployment") > 0 and self._income(member, "wages") <= 0

    def weekly_rate(self, member: HouseholdMember) -> int:
        """85% of average weekly wages on the working route, else the weekly unemployment rate;
        each rounded down to the dollar, then capped."""
        if self.on_working_route(member):
            rate = self._floor(BENEFIT_RATE * self._decimal_income(member, "wages") / WEEKS_PER_YEAR)
            return min(rate, self.figures.max_weekly_rate)

        rate = self._floor(self._decimal_income(member, "unemployment") / WEEKS_PER_YEAR)
        cap = self.unemployment_max_weekly_rate()
        return rate if cap is None else min(rate, cap)

    def lump_sum(self, weekly_rate: int, days: int) -> int:
        """The weekly rate over `days`, rounded half-up to the dollar. Floored at 1, since an
        eligible member valued at 0 is hidden by the results page."""
        total = (Decimal(weekly_rate) * days / DAYS_PER_WEEK).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return max(int(total), 1)

    @cached_property
    def figures(self) -> PaidLeaveYear:
        """The screening year's figures; a year with none uses the latest and is reported to
        Sentry rather than raising, since an exception drops the program from results."""
        year = self.screen.get_reference_date().year
        if year in PAID_LEAVE_YEARS:
            return PAID_LEAVE_YEARS[year]

        latest = max(PAID_LEAVE_YEARS)
        capture_message(
            f"No NJ TDI/FLI figures for {year}; using {latest}.",
            level="error",
        )
        return PAID_LEAVE_YEARS[latest]

    @staticmethod
    def _income(member: HouseholdMember, income_type: str) -> float:
        return member.calc_gross_income("yearly", [income_type])

    def _decimal_income(self, member: HouseholdMember, income_type: str) -> Decimal:
        return Decimal(str(self._income(member, income_type)))

    @staticmethod
    def _floor(amount: Decimal) -> int:
        return int(amount.quantize(Decimal("1"), rounding=ROUND_FLOOR))
