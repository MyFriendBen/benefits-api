"""NJ Child Care Assistance Program (CCAP)."""

from decimal import Decimal

from programs.programs.cross_white_label.ccdf.base import WORK_INCOME_TYPES, Ccdf
from programs.programs.shared.age import age_in_months
from programs.programs.shared.income import fpl_income_limit
from screener.models import HouseholdMember


class NjCcap(Ccdf):
    """
    New Jersey CCAP, the state's CCDF subsidy. Inherits the federal rules from ``Ccdf``; New
    Jersey sets these:

    - Income: yearly income, leaving out room rent and cash assistance, at most 200% of the
      poverty level for the household size. The 2026-2027 schedule is 200% of the 2026 HHS
      guidelines, so the limit reads the program's poverty year.
    - Activity: a parent works 30 hours a week, studies full time, or is in job training.
      Hours are asked only for hourly pay, so a parent paid any other way counts as working
      30 hours; a parent's hourly jobs are added together, but work, school and training never
      are. Any job training counts, since the screener does not ask its hours, and full-time
      study is the screener's "half-time or more", not New Jersey's 12 credit hours.
    - Value: the licensed center full-time rate for each eligible child's age band, less a
      copay of 4% of yearly income for one child or 6% for two or more, on the same income the
      limit counts. The copay is waived at or below the poverty level. Age bands are counted
      in whole months from the birth month, and a child takes the older band from the month
      they reach it.

    Not evaluated: special needs at 13 to 18, part-time care, provider type and star rating,
    and the copay waiver for protective services.

    The spec is ``programs/cross_white_label/ccdf/nj/ccdf_nj_spec.md`` in program-ops.
    """

    program_code = "nj_ccap"

    dependencies = tuple(dependency for dependency in Ccdf.dependencies if dependency != "student")

    income_exclusions = ("boarder", "cashAssistance", "cashAssistanceOther")
    income_limit_fpl_percent = 2

    min_weekly_work_hours = 30

    #: Licensed center full-time monthly rates, as (first month of age, rate), youngest first.
    payment_rates = (
        (0, Decimal("1591.66")),
        (18, Decimal("1417.54")),
        (30, Decimal("1265.66")),
        (60, Decimal("1193.54")),
    )

    one_child_copay_rate = Decimal("0.04")
    two_plus_copay_rate = Decimal("0.06")

    def income_limit(self) -> int:
        return fpl_income_limit(self.program.year, self.screen.household_size, self.income_limit_fpl_percent)

    def parent_is_active(self, parent: HouseholdMember) -> bool:
        work = [stream for stream in parent.income_streams.all() if stream.type in WORK_INCOME_TYPES]
        if any(stream.frequency != "hourly" for stream in work):
            return True

        hourly_hours = sum(stream.hours_worked or 0 for stream in work if stream.frequency == "hourly")
        if hourly_hours >= self.min_weekly_work_hours:
            return True

        return parent.student_full_time is True or parent.student_job_training_program is True

    def payment_rate(self, child: HouseholdMember) -> Decimal:
        months = age_in_months(child)
        rate = self.payment_rates[0][1]
        for first_month, band_rate in self.payment_rates:
            if months >= first_month:
                rate = band_rate

        return rate

    def family_copayment(self, children: list[HouseholdMember]) -> Decimal:
        income = self.countable_income()
        if income <= self.program.year.get_limit(self.screen.household_size):
            return Decimal(0)

        copay_rate = self.one_child_copay_rate if len(children) == 1 else self.two_plus_copay_rate
        return copay_rate * income / 12
