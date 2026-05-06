import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class WaCsfp(ProgramCalculator):
    """
    Commodity Supplemental Food Program (CSFP) — Washington State.

    Provides free monthly food commodity boxes to seniors aged 60+ with household
    income at or below 150% FPL. Value is estimated at $50/month per eligible member.

    Data gaps (not evaluated by this calculator):
      - CSFP service area: not all WA counties/areas are served; local agency coverage
        varies and no maintained lookup table exists in the screener.
      - FDPIR exclusion: 7 CFR 247.9(c) prohibits dual participation with the Food
        Distribution Program on Indian Reservations; no screener field for FDPIR.
      - Slot availability: caseload is federally capped; waitlists may apply locally.

    State residency is enforced via the `wa` white label routing.
    """

    min_age = 60
    fpl_percent = 1.5
    member_amount = 50

    dependencies = [
        "age",
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        e.condition(member.age is not None and member.age >= self.min_age)

    def household_eligible(self, e: Eligibility):
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
