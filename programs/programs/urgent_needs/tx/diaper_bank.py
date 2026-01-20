from ..base import UrgentNeedFunction


class NationalDiaperBankNetwork(UrgentNeedFunction):
    """Texas Diaper Bank Program via the National Diaper Bank Network.

    Provides diaper assistance to families with young children in specific counties.
    Eligibility criteria include having a child under 5 years old, needing baby supplies,
    and having child support expenses.

    More info: https://nationaldiaperbanknetwork.org/member-directory/
    """

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
        # Check if county is eligible
        is_eligible_county = self.screen.county in self.eligible_counties
        if not is_eligible_county:
            return False

        # age under 5
        has_young_child = self.screen.num_children(age_max=self.max_age) > 0
        has_needs_baby_supplies = self.screen.needs_baby_supplies

        # Check if there are any child support expenses
        has_child_support_expense = self.screen.has_expense(["childSupport"])
        return has_young_child and has_needs_baby_supplies and has_child_support_expense
