from ..base import UrgentNeedFunction


class ParentsAsTeacher(UrgentNeedFunction):
    dependencies = ["age", "county"]
    counties = [
        "Adams County",
        "Alamosa County",
        "Arapahoe County",
        "Bent County",
        "Boulder County",
        "Conejos County",
        "Costilla County",
        "Crowley County",
        "Delta County",
        "Denver County",
        "Dolores County",
        "El Paso County",
        "Fremont County",
        "Gunnison County",
        "Huerfano County",
        "Jefferson County",
        "La Plata County",
        "Larimer County",
        "Las Animas County",
        "Mesa County",
        "Montezuma County",
        "Montrose County",
        "Morgan County",
        "Otero County",
        "Ouray County",
        "Park County",
        "Pueblo County",
        "Routt County",
        "Saguache County",
        "San Miguel County",
        "Teller County",
    ]
    max_age = 5

    def eligible(self):
        """
        Return True if there is a child younger than 5 and lives in an eligible county
        """
        age_eligible = self.screen.num_children(age_max=self.max_age) > 0
        county_eligible = self.screen.county in self.counties

        return age_eligible and county_eligible
