from ..base import UrgentNeedFunction


class NationalDiaperBankNetwork(UrgentNeedFunction):
    """Texas Diaper Bank Program via the National Diaper Bank Network.

    Provides diaper assistance to families with young children in specific counties.
    Eligibility criteria include having a child under 5 years old, needing baby supplies,
    and having child support expenses.

    More info: https://nationaldiaperbanknetwork.org/member-directory/
    """

    dependencies = ["age"]
    max_age = 4

    def eligible(self) -> bool:
        return self.screen.num_children(age_max=self.max_age) > 0
