from ..base import UrgentNeedFunction


class NationalDiaperBankNetwork(UrgentNeedFunction):
    dependencies = ["age", "county"]
    max_age = 4
    eligible_counties = [
        "Travis",
        "Dallas",
        "El Paso",
        "Tarrant",
        "Galveston",
        "Brazoria",
        "Collin",
        "Bexar",
        "McLennan",
    ]

    def eligible(self):
        is_eligible_county = self.screen.county in self.eligible_counties
        print(f"County: {self.screen.county}, Eligible: {is_eligible_county}")
        if not is_eligible_county:
            return False

        # age under 5
        has_young_child = self.screen.num_children(age_max=self.max_age) > 0
        has_needs_baby_supplies = self.screen.needs_baby_supplies
        # Check if there are any child support expenses
        has_child_support_expense = self.screen.has_expense(["childSupport"])
        return has_young_child and has_needs_baby_supplies and has_child_support_expense
