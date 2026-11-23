from ..base import UrgentNeedFunction


class BiaFoodDelivery(UrgentNeedFunction):
    dependencies = ["county"]
    eligible_counties = [
        "Adams County",
        "Arapahoe County",
        "Denver County",
        "Jefferson County",
    ]

    def eligible(self):
        """
        Return True if in Adams, Arapahoe, Denver or Jefferson county
        """
        return self.screen.county in self.eligible_counties
