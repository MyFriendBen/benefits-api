from ..base import UrgentNeedFunction


class EarlyIntervention(UrgentNeedFunction):
    dependencies = ["age", "county"]
    max_age = 5

    def eligible(self):
        # age under 5
        return self.screen.num_children(age_max=self.max_age) > 0
