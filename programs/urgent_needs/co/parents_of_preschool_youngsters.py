from ..base import UrgentNeedFunction


class ParentsOfPreschoolYoungsters(UrgentNeedFunction):
    dependencies = ["age", "county"]
    counties = [
        "Adams County",
        "Alamosa County",
        "Arapahoe County",
        "Costilla County",
        "Crowley County",
        "Denver County",
        "Dolores County",
        "Jefferson County",
        "Montezuma County",
        "Otero County",
        "Pueblo County",
        "Saguache County",
        "Weld County",
    ]
    min_age = 2
    max_age = 5

    def eligible(self):
        """
        Return True if a child is between 2 and 5 and lives in an eligible county
        """
        age_eligible = self.screen.num_children(age_min=self.min_age, age_max=self.max_age) > 0
        county_eligible = self.screen.county in self.counties

        return age_eligible and county_eligible
