from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages


class NCLieap(ProgramCalculator):
    fpl_percent = 1.3
    expenses = ["rent", "mortgage", "heating"]
    dependencies = [
        "income_frequency",
        "income_amount",
        "household_size",
    ]
    large_household_size = 4
    max_value_fpl_percent = 0.5
    small_household_low_income_value = 400
    small_household_large_income_value = 300
    large_household_low_income_value = 500
    large_household_large_income_value = 400

    def household_eligible(self, e: Eligibility):
        household_size = self.screen.household_size

        # has rent, mortgage or heating expense
        has_program_expense = self.screen.has_expense(NCLieap.expenses)
        e.condition(has_program_expense)

        # income
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.as_dict()[household_size])
        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))

    def household_value(self):
        household_size = self.screen.household_size
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.as_dict()[household_size])

        if household_size < self.large_household_size:
            if gross_income <= income_limit * self.max_value_fpl_percent:
                return self.small_household_low_income_value
            elif gross_income <= income_limit:
                return self.small_household_large_income_value
        else:
            if gross_income <= income_limit * self.max_value_fpl_percent:
                return self.large_household_low_income_value
            elif gross_income <= income_limit:
                return self.large_household_large_income_value
