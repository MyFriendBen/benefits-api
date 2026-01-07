from ..base import UrgentNeedFunction


class LawHelp(UrgentNeedFunction):
    """
    Texas Law Help

    Find free or discounted legal services in your county.
    """

    dependencies = ["income_amount", "income_frequency", "household_size"]
    fpl_percent = 1.25

    def eligible(self):

        # All TX counties; 125% of the federal poverty line.

        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.urgent_need.year.as_dict()[self.screen.household_size] * self.fpl_percent

        return income <= income_limit
