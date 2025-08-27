from ..base import UrgentNeedFunction


class Rentervention(UrgentNeedFunction):
    def eligible(self):
        # Condition 1: Household needs housing/utilities help
        needs_housing_help = self.screen.needs_housing_help

        # Condition 2: Household has rent expense
        has_rent = self.screen.has_expense(["rent"])

        return needs_housing_help and has_rent
