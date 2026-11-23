from ..base import UrgentNeedFunction


class IlEarlyIntervention(UrgentNeedFunction):
    dependencies = ["age"]
    max_age = 2

    def eligible(self):
        """
        Has child age 0-2
        """
        return self.screen.num_children(age_max=self.max_age) > 0
