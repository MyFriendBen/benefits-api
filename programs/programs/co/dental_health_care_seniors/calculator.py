from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class DentalHealthCareSeniors(ProgramCalculator):
    member_amount = 80 * 12
    min_age = 60
    percent_of_fpl = 2.5
    ineligible_insurance = ["medicaid", "private"]
    dependencies = ["age", "income_amount", "income_frequency", "insurance", "household_size"]

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            e.condition(False)
            return
        # Income test
        fpl = self.program.year.as_dict()
        gross_income = int(self.screen.calc_gross_income("monthly", ["all"]))
        income_band = int(DentalHealthCareSeniors.percent_of_fpl * fpl[self.screen.household_size] / 12)
        e.condition(gross_income <= income_band, messages.income(gross_income, income_band))

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        if member.age is None:
            return

        # insurance
        e.condition(not member.insurance.has_insurance_types(DentalHealthCareSeniors.ineligible_insurance))

        # age
        e.condition(member.age >= DentalHealthCareSeniors.min_age)
