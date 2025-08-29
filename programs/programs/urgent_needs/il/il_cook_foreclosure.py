from ..base import UrgentNeedFunction


class IlCookForeclosure(UrgentNeedFunction):

    def eligible(self):
        # expenses
        has_mortgage = self.screen.has_expense(["mortgage"])

        return has_mortgage
