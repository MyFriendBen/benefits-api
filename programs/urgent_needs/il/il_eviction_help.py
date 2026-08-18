from ..base import UrgentNeedFunction


class IlEvictionHelp(UrgentNeedFunction):
    def eligible(self):
        """
        Eviction Help Illinois

        Return True if HH marks need for housing/utilities resource and HH has rent expense
        """
        has_rent = self.screen.has_expense(["rent"])

        return has_rent
