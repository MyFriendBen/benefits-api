from ..base import UrgentNeedFunction
from integrations.services.income_limits import ami


class IlRenterAssistance(UrgentNeedFunction):
    ami_percent = "80%"
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]

    def eligible(self):
        """
        Return True if the household is at or below 80% AMI using HUD 2025 income limits
        """

        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.urgent_need.year.period, limit_type="il")

        income = self.screen.calc_gross_income("yearly", ["all"])
        needs_housing_help = self.screen.needs_housing_help
        has_rent = self.screen.has_expense(["rent"])

        return needs_housing_help and has_rent and income <= income_limit
