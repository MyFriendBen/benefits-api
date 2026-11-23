from integrations.services.income_limits import ami
from ..base import UrgentNeedFunction


class Raft(UrgentNeedFunction):
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]
    ami_percent = "50%"

    def eligible(self):
        # income
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.urgent_need.year.period, limit_type="il")
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_eligible = income <= income_limit

        # expenses
        has_expense = self.screen.has_expense(["rent", "mortgage", "subsidizedRent"])

        return income_eligible and has_expense
