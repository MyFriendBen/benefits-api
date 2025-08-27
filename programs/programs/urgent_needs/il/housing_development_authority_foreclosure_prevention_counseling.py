from ..base import UrgentNeedFunction


class HousingDevelopmentAuthorityForeclosurePreventionCounseling(UrgentNeedFunction):

    def eligible(self):
        """
        Return True if the household marks need for housing/utilities resource and household has a mortgage expense
        """

        needs_housing_help = self.screen.needs_housing_help
        has_mortgage = self.screen.has_expense(["mortgage"])

        return needs_housing_help and has_mortgage
