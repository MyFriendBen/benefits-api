from ..base import UrgentNeedFunction


class LawyersClearinghouse(UrgentNeedFunction):
    dependencies = ["income_amount", "income_frequency", "household_size"]
    fpl_percent = 2

    def eligible(self):
        # income
        income_limit = self.urgent_need.year.as_dict()[self.screen.household_size] * self.fpl_percent
        income = self.screen.calc_gross_income("yearly", ["all"])
        return income <= income_limit
