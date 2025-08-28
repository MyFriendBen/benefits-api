from ..base import UrgentNeedFunction


class IlForeclosurePreventionCounseling(UrgentNeedFunction):
    def eligible(self):
        """
        Illinois Housing Development Authority Foreclosure Prevention Counseling

        Return True if HH marks need for housing/utilities resource and HH has a mortgage expense
        """
        has_mortgage = self.screen.has_expense(["mortgage"])

        return needs_housing_help and has_mortgage
