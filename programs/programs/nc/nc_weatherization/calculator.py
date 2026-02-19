from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages


class NCWeatherization(ProgramCalculator):
    fpl_percent = 2
    expenses = [
        "rent",
        "mortgage",
        "heating",
        "cooling",
        "otherUtilities",
        "propertyTax",
        "homeownersInsurance",
        "hoa",
    ]
    dependencies = ["household_size", "income_amount", "income_frequency"]
    amount = 300

    def household_eligible(self, e: Eligibility):
        household_size = self.screen.household_size

        # has expenses
        has_program_expenses = self.screen.has_expense(NCWeatherization.expenses)
        e.condition(has_program_expenses)

        # income
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.as_dict()[household_size])
        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))
