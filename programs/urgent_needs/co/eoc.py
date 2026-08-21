from integrations.services.income_limits import ami
from ..base import UrgentNeedFunction


class Eoc(UrgentNeedFunction):
    ami_percent = "80%"
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]

    def eligible(self):
        """
        Return True if the household is below the income limit for their county and household size
        """
        # income
        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.urgent_need.year.period)

        # has rent or mortgage expense
        has_rent_or_mortgage = self.screen.has_expense(["rent", "mortgage"])

        return income <= income_limit and has_rent_or_mortgage
