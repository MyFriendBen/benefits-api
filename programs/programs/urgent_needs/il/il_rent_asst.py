from ..base import UrgentNeedFunction
from integrations.clients.hud_income_limits import hud_client
from integrations.clients.hud_income_limits.client import Section8AmiPercent


class IlRenterAssistance(UrgentNeedFunction):
    ami_percent: Section8AmiPercent = "80%"
from typing import ClassVar

from ..base import UrgentNeedFunction
from integrations.clients.hud_income_limits import hud_client
from integrations.clients.hud_income_limits.client import Section8AmiPercent


class IlRenterAssistance(UrgentNeedFunction):
    ami_percent: Section8AmiPercent = "80%"
    dependencies: ClassVar[list[str]] = ["income_amount", "income_frequency", "household_size", "county"]

    def eligible(self) -> bool:
        """
        Return True if the household is at or below 80% AMI using HUD Standard Section 8 Income Limits.

        Per CBRAP requirements: https://www.illinoishousinghelp.org/cbrap
        """

        income_limit = hud_client.get_screen_il_ami(
            self.screen, self.ami_percent, self.urgent_need.year.period if self.urgent_need.year else 2025
        )
        income = self.screen.calc_gross_income("yearly", ["all"])
        below_income_limit = income <= income_limit

        needs_housing_help = bool(self.screen.needs_housing_help)

        has_rent = self.screen.has_expense(["rent"])

        return needs_housing_help and has_rent and below_income_limit
