from typing import ClassVar

from ..base import UrgentNeedFunction
from integrations.clients.hud_income_limits import hud_client
from integrations.clients.hud_income_limits.client import Section8AmiPercent


class IlRenterAssistance(UrgentNeedFunction):
    ami_percent: Section8AmiPercent = "80%"
    dependencies: ClassVar[list[str]] = ["income_amount", "income_frequency", "household_size", "county"]

    def eligible(self) -> bool:
        """
        Determine eligibility for Illinois Court-Based Rental Assistance Program (CBRAP).

        Eligibility criteria:
        - Household income at or below 80% Area Median Income (AMI)
        - Household needs housing assistance
        - Household has rent expenses

        Uses HUD Standard Section 8 Income Limits API for AMI calculation.

        Returns:
            bool: True if household meets all eligibility criteria, False otherwise.

        Raises:
            ValueError: If urgent_need.year is not set.

        Reference: https://www.illinoishousinghelp.org/cbrap
        """

        if not self.urgent_need.year:
            raise ValueError("urgent_need.year must be set for IL rent assistance eligibility")

        income_limit = hud_client.get_screen_il_ami(self.screen, self.ami_percent, self.urgent_need.year.period)
        income = self.screen.calc_gross_income("yearly", ["all"])
        below_income_limit = income <= income_limit

        needs_housing_help = bool(self.screen.needs_housing_help)

        has_rent = self.screen.has_expense(["rent"])

        return needs_housing_help and has_rent and below_income_limit
