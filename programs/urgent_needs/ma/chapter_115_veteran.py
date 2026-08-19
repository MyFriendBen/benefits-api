from ..base import UrgentNeedFunction


class Chapter115Veteran(UrgentNeedFunction):
    dependencies = ["household_assets", "income_amount", "income_frequency", "household_size"]
    fpl_percent = 2
    asset_limit_indv = 8_400
    asset_limit_joint = 16_600

    def eligible(self):
        # income
        income_limit = self.urgent_need.year.as_dict()[self.screen.household_size] * self.fpl_percent
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_eligible = income <= income_limit

        # assets
        asset_limit = self.asset_limit_joint if self.screen.is_joint() else self.asset_limit_indv
        asset_eligible = int(self.screen.household_assets) <= asset_limit

        return income_eligible and asset_eligible
