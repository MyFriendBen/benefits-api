from integrations.services.income_limits import ami
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages


class EmergencyRentalAssistance(ProgramCalculator):
    program_code = "erap"
    amount = 13_848
    ami_percent = "80%"
    expenses = ["rent"]
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]

    def household_eligible(self, e: Eligibility):
        # Income test
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period)
        e.condition(income < income_limit, messages.income(income, income_limit))

        # has rent expense
        has_rent = self.screen.has_expense(EmergencyRentalAssistance.expenses)
        e.condition(has_rent)
