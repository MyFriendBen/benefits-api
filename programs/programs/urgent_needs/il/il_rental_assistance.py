from ..base import UrgentNeedFunction
from integrations.services.income_limits import ami


class IlRenterAssistance(UrgentNeedFunction):
    ami_percent = "80%"
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]
    

    def eligible(self):
        """
        Return True if the household is at or below 80% the income limit for their household size
        """
        print(f"IlRenterAssistance.eligible() called for screen {self.screen.county}")
        # income_limit = ami.get_screen_ami(
        #     self.screen, self.ami_percent, self.urgent_need.year.period, limit_type="il"
        # )
        income = self.screen.calc_gross_income("yearly", ["all"])

        # # Condition 1: Household needs housing/utilities help
        needs_housing_help = self.screen.needs_housing_help

        # # Condition 2: Household has rent expense
        has_rent = self.screen.has_expense(["rent"])

        # # Remove this debug code before creating PR
        print(
            f"Income Limit: {income}, Income: {income}, needs_housing_help: {needs_housing_help}, has_rent: {has_rent}"
        )

        # return needs_housing_help and has_rent and income <= income_limit
        return needs_housing_help and has_rent
