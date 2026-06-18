from integrations.services.income_limits import ami
from ..base import UrgentNeedFunction


class Trua(UrgentNeedFunction):
    ami_percent = "80%"
    dependencies = ["household_size", "income_amount", "income_frequency", "county"]

    def eligible(self):
        """
        Return True if the household is below the income limit for their household size
        """
        if self.urgent_need.year is None:
            return False
        household_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.urgent_need.year.period, limit_type="il")
        has_rent_or_mortgage = self.screen.has_expense(["rent"])

        return household_income <= income_limit and has_rent_or_mortgage
