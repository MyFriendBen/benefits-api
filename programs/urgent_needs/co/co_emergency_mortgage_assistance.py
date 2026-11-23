from integrations.services.income_limits import ami
from ..base import UrgentNeedFunction


class CoEmergencyMortgageAssistance(UrgentNeedFunction):
    ami_percent = 1.5
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]

    def eligible(self):
        income = int(self.screen.calc_gross_income("yearly", ["all"]))

        income_limit = ami.get_screen_ami(self.screen, "100%", self.urgent_need.year.period) * self.ami_percent
        has_mortgage = self.screen.has_expense(["mortgage"])

        return income <= income_limit and has_mortgage
