from ..base import UrgentNeedFunction


class DenverEmergencyAssistance(UrgentNeedFunction):
    dependencies = ["county", "income_amount", "income_frequency", "household_size"]
    county = "Denver County"
    fpl_percent = 4

    def eligible(self):
        """
        Return True if the household is bellow 400% fpl and lives in Denver
        """
        county_eligible = self.screen.county == self.county
        fpl = self.urgent_need.year.as_dict()
        income_eligible = (
            self.screen.calc_gross_income("yearly", ["all"]) < fpl[self.screen.household_size] * self.fpl_percent
        )
        has_rent_or_mortgage = self.screen.has_expense(["rent", "mortgage"])

        return county_eligible and income_eligible and has_rent_or_mortgage
