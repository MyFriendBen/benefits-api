from ..base import UrgentNeedFunction


class il_beacon(UrgentNeedFunction):
    dependencies = ["age"]
    min_age = 5
    max_age = 21

    def eligible(self):
        """
        Has child age 5-21
        """

        return self.screen.num_children(age_min=self.min_age, age_max=self.max_age) > 0
