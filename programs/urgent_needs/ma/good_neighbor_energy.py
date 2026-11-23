from integrations.services.income_limits import smi
from ..base import UrgentNeedFunction


class GoodNeighborEnergy(UrgentNeedFunction):
    dependencies = ["income_amount", "income_frequency", "household_size"]
    min_income_percent = 0.6
    max_income_percent = 0.8

    def eligible(self):
        # income
        smi_amount = smi.get_screen_smi(self.screen, self.urgent_need.year.period)
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_eligible = smi_amount * self.min_income_percent < income <= smi_amount * self.max_income_percent

        # expenses
        has_expense = self.screen.has_expense(["rent", "mortgage", "subsidizedRent"])

        return income_eligible and has_expense
