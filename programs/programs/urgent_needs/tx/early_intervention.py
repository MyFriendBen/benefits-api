from ..base import UrgentNeedFunction


class EarlyIntervention(UrgentNeedFunction):
    dependencies = ["age", "county"]
    max_age = 5

    def eligible(self):
        # age under 5
        has_young_child = self.screen.num_children(age_max=self.max_age) > 0
        has_dev_concern = self.screen.needs_child_dev_help
        return has_young_child and has_dev_concern
