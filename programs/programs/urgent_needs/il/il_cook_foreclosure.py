from ..base import UrgentNeedFunction


class IlCookForeclosure(UrgentNeedFunction):
    dependencies = ["county"]
    county = "Cook"

    def eligible(self):
        # county
        county_eligible = self.screen.county == self.county

        # expenses
        has_mortgage = self.screen.has_expense(["mortgage"])

        return county_eligible and has_mortgage
