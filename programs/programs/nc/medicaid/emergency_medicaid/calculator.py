from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class NcEmergencyMedicaid(ProgramCalculator):
    # $6,268/yr | ~$522/mo
    member_amount = 6268
    max_age = 64
    fpl_percent = 1.96
    dependencies = [
        "age",
        "insurance",
        "income_amount",
        "income_frequency",
        "household_size",
    ]

    def household_eligible(self, e: Eligibility):
        fpl_percent = self.fpl_percent

        for member in self.screen.household_members.all():
            # Pregnant and under 18 years old have a different FPL percentage
            if member.age <= 18 and member.pregnant:
                fpl_percent = 2.11

        # Medicaid eligibility
        e.condition(medicaid_eligible(self.data), messages.must_have_benefit("Medicaid"))

        # Income
        fpl = self.program.year
        income_limit = int(fpl_percent * fpl.get_limit(self.screen.household_size))
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(member.age < self.max_age)
