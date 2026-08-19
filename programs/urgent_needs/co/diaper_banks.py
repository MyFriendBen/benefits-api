from ..base import UrgentNeedFunction

DIAPER_BANK_COUNTIES = [
    "Adams County",
    "Arapahoe County",
    "Boulder County",
    "Broomfield County",
    "Denver County",
    "Douglas County",
    "Jefferson County",
    "Larimer County",
    "Mesa County",
    "Weld County",
]


class FamilyResourceCenterAssociation(UrgentNeedFunction):
    ineligible_counties = DIAPER_BANK_COUNTIES

    def eligible(self):
        """
        Return True for users who live in an eligible county
        """

        return self.screen.county not in self.ineligible_counties


class NationalDiaperBank(UrgentNeedFunction):
    eligible_counties = DIAPER_BANK_COUNTIES

    def eligible(self):
        """
        Return True for users who live in an eligible county
        """

        return self.screen.county in self.eligible_counties
