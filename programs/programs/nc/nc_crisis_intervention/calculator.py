from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages


class NCCrisisIntervention(ProgramCalculator):
    expenses = ["rent", "mortgage", "heating", "cooling"]
    fpl_percent = 1.5
    amount = 600

    dependencies = [
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def household_eligible(self, e: Eligibility):
        household_size = self.screen.household_size

        # has rent or mortgage expense
        has_rent_or_mortgage = self.screen.has_expense(NCCrisisIntervention.expenses)
        e.condition(has_rent_or_mortgage)

        # income
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.as_dict()[household_size])
        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))
