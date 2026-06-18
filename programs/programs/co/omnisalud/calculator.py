from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages


class OmniSalud(ProgramCalculator):
    income_percent = 1.5
    insurance = ["none"]
    member_amount = 610 * 12
    dependencies = ["income_amount", "income_frequency", "household_size", "age", "insurance"]

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            return
        # Income test
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.program.year.as_dict()[self.screen.household_size] * OmniSalud.income_percent
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # insurance
        e.condition(member.insurance.has_insurance_types(OmniSalud.insurance))
