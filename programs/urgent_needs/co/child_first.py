from ..base import UrgentNeedFunction


class ChildFirst(UrgentNeedFunction):
    dependencies = ["age", "county"]
    max_age = 5
    eligible_counties = [
        "Adams County",
        "Alamosa County",
        "Arapahoe County",
        "Bent County",
        "Boulder County",
        "Broomfield County",
        "Chaffee County",
        "Clear Creek County",
        "Conejos County",
        "Costilla County",
        "Crowley County",
        "Custer County",
        "Douglas County",
        "El Paso County",
        "Fremont County",
        "Gilpin County",
        "Jefferson County",
        "Lake County",
        "Mineral County",
        "Otero County",
        "Rio Grand County",
        "Routt County",
        "Saguache County",
        "Weld County",
    ]

    def eligible(self):
        """
        Return True if the household has a child aged 0-5 and lives in an eligible county
        """
        is_age_eligible = self.screen.num_children(age_max=self.max_age) > 0

        return is_age_eligible and self.screen.county in self.eligible_counties
