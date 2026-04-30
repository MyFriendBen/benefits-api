from ..base import UrgentNeedFunction


class NationalDiaperBankNetwork(UrgentNeedFunction):
    """Texas Diaper Bank Program via the National Diaper Bank Network.

    Provides diaper assistance to families with young children in specific counties
    who have a need for diapers and other baby supplies.

    Code-level eligibility requires at least one child under 5 years old.
    County restrictions and the "Diapers and other baby supplies" need check
    are configured via the admin UI (county eligibility and required needs fields).

    More info: https://nationaldiaperbanknetwork.org/member-directory/
    """

    dependencies = ["age", "county"]
    max_age = 4

    def eligible(self) -> bool:
        return self.screen.num_children(age_max=self.max_age) > 0
