from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages


class NcEmergencyMedicaid(ProgramCalculator):
    program_code = "nc_emergency_medicaid"
    # PolicyEngine-backed, and a genuine dependency rather than a proxied income test:
    # the rule is about whether Medicaid already covers this household, which is not
    # reducible to a condition on the household's own facts. PE resolves it through a
    # dozen category tests, so there is nothing to restate.
    gates_on = ("nc_medicaid",)
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
        e.condition(self.program_eligible("nc_medicaid"), messages.must_have_benefit("Medicaid"))

        # Income
        fpl = self.program.year
        income_limit = int(fpl_percent * fpl.get_limit(self.screen.household_size))
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(member.age < self.max_age)
