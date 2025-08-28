from ..base import UrgentNeedFunction


class IlSaveHome(UrgentNeedFunction):

    def eligible(self):
        """
        Illinois Housing Development Authority Foreclosure Prevention Counseling

        Return True if the household marks need for housing/utilities resource and household has a mortgage expense
        """

        has_mortgage = self.screen.has_expense(["mortgage"])

        return has_mortgage
