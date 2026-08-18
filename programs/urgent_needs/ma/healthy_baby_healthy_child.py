from ..base import UrgentNeedFunction


class HealthyBabyHealthyChild(UrgentNeedFunction):
    dependencies = ["age", "county"]
    max_age = 4
    cities = ["Boston"]

    def eligible(self):
        # age
        age_eligble = self.screen.num_children(age_max=self.max_age, include_pregnant=True) > 0

        # location
        city_eligible = self.screen.county in self.cities

        return age_eligble and city_eligible
