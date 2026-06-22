from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages


class SunBucks(ProgramCalculator):
    member_amount = 120
    min_age = 7
    max_age = 16
    fpl_percent = 1.85
    dependencies = ["age", "insurance", "income_amount", "income_frequency", "household_size"]

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            e.condition(False)
            return
        # Income
        fpl = self.program.year
        income_limit = int(self.fpl_percent * fpl.get_limit(self.screen.household_size))
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        # Must not have the following benefits
        e.condition(not self.screen.has_benefit("snap"), messages.must_not_have_benefit("snap"))
        e.condition(not self.screen.has_benefit("tanf"), messages.must_not_have_benefit("tanf"))

        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # age eligibility
        if member.age is None:
            return
        e.condition(SunBucks.min_age <= member.age <= SunBucks.max_age)

        e.condition(not member.has_insurance("medicaid"))
