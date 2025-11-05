from ..base import UrgentNeedFunction
from integrations.clients.hud_income_limits import hud_client, AmiPercent


class IlRenterAssistance(UrgentNeedFunction):
    ami_percent: AmiPercent = "80%"
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]

    def eligible(self) -> bool:
        """
        Return True if the household is at or below 80% AMI using HUD 2025 income limits
        """

        income_limit = hud_client.get_screen_ami(
            self.screen, self.ami_percent, self.urgent_need.year.period if self.urgent_need.year else 2025
        )
        income = self.screen.calc_gross_income("yearly", ["all"])
        below_income_limit = income <= income_limit

        needs_housing_help = bool(self.screen.needs_housing_help)

        has_rent = self.screen.has_expense(["rent"])

        return needs_housing_help and has_rent and below_income_limit
