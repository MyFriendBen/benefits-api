from typing import ClassVar

import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember


class WaOrcaLift(ProgramCalculator):
    """ORCA LIFT Reduced Fare Program - discounted $1.00 transit fares for lower-income
    adults aged 19–64 in the Puget Sound region (King, Pierce, Snohomish, Kitsap counties).

    Eligibility requires at least one household member aged 19-64 AND one of:
      - Categorical: Apple Health (Medicaid), Washington Basic Food (SNAP), or WIC enrollment
      - Income: household gross income at or below 200% FPL

    Data gap: WA State Opportunity Grant pathway (Criterion 3) is skipped — grant recipients
    must be ≤200% FPL to receive the grant, so they are captured by the income pathway in
    most cases. Surfaced in program description for edge cases.

    Value: $864/year per eligible cardholder (= $72/month PugetPass differential x 12).
    """

    min_age = 19
    max_age = 64
    fpl_percent = 2.0
    member_amount = 864  # $72/month x 12 months (monthly PugetPass fare differential)
    dependencies: ClassVar[list[str]] = [
        "age",
        "income_amount",
        "income_frequency",
        "household_size",
    ]

    def _member_age(self, member: HouseholdMember) -> int | None:
        if member.birth_year_month is not None:
            return member.calc_age()
        return member.age

    def member_eligible(self, e: MemberEligibility) -> None:
        age = self._member_age(e.member)
        e.condition(age is not None and self.min_age <= age <= self.max_age)

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            return
        categorical = (
            self.screen.has_benefit("wa_snap")
            or self.screen.has_benefit("wa_wic")
            or any(
                member.has_insurance("wa_apple_health_medicaid") or member.has_insurance("wa_apple_health_for_kids")
                for member in self.screen.household_members.all()
            )
        )

        if categorical:
            e.condition(True, messages.presumed_eligibility())
        else:
            gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
            income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
