from datetime import date
from typing import Optional
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
from programs.programs import messages


class WaSsdi(ProgramCalculator):
    """SSDI provides monthly payments to people who cannot work due to disability or blindness.
    Uses per-member eligibility with birth-year-based FRA schedule and dual SGA thresholds.
    Assumes sufficient work credits (data gap — screener does not capture work history).
    """

    sga_non_blind = 1_690
    sga_blind = 2_830
    member_amount = 1_634
    dependencies = [
        "age",
        "income_amount",
        "income_frequency",
    ]

    # SSA Full Retirement Age schedule by birth year
    # Born 1943–1954: FRA = 66y 0m
    # Born 1955: 66y 2m, 1956: 66y 4m, 1957: 66y 6m, 1958: 66y 8m, 1959: 66y 10m
    # Born 1960+: 67y 0m
    FRA_SCHEDULE: list[tuple[int, int, int]] = [
        (1954, 66, 0),
        (1955, 66, 2),
        (1956, 66, 4),
        (1957, 66, 6),
        (1958, 66, 8),
        (1959, 66, 10),
    ]

    @staticmethod
    def _get_fra(birth_year: int) -> tuple[int, int]:
        if birth_year <= 1954:
            return (66, 0)
        if birth_year >= 1960:
            return (67, 0)
        for max_year, years, months in WaSsdi.FRA_SCHEDULE:
            if birth_year <= max_year:
                return (years, months)
        return (67, 0)

    @staticmethod
    def _is_under_fra(birth_year: int, birth_month: Optional[int], reference_date: date) -> bool:
        fra_years, fra_months = WaSsdi._get_fra(birth_year)

        if birth_month is None:
            birth_month = 1

        fra_date = date(
            birth_year + fra_years + (birth_month + fra_months - 1) // 12, (birth_month + fra_months - 1) % 12 + 1, 1
        )

        return reference_date < fra_date

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        e.condition(member.long_term_disability is True)

        if member.birth_year is not None:
            e.condition(self._is_under_fra(member.birth_year, member.birth_month, self.screen.get_reference_date()))

        earned_income = int(member.calc_gross_income("monthly", ["earned"]))
        sga_limit = self.sga_blind if member.visually_impaired else self.sga_non_blind
        e.condition(earned_income <= sga_limit)

        already_receiving_ssdi = member.calc_gross_income("yearly", ["sSDisability"]) > 0
        e.condition(not already_receiving_ssdi)

        already_receiving_ss_retirement = member.calc_gross_income("yearly", ["sSRetirement"]) > 0
        e.condition(not already_receiving_ss_retirement)

    def household_eligible(self, e: Eligibility):
        e.condition(
            not self.screen.has_benefit("ssdi"),
            messages.must_not_have_benefit("SSDI"),
        )

        has_disability = any(me.eligible for me in e.eligible_members)
        e.condition(has_disability, messages.has_disability())
