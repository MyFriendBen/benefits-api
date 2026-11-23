from ..base import UrgentNeedFunction


class EarlyIntervention(UrgentNeedFunction):
    dependencies = ["age"]
    max_age = 2

    def eligible(self):
        # age
        return self.screen.num_children(age_max=self.max_age) > 0
