from ..base import UrgentNeedFunction


class FamilySupportCenters(UrgentNeedFunction):
    def eligible(self):
        # disability
        for member in self.screen.household_members.all():
            if member.has_disability():
                return True
        return False
