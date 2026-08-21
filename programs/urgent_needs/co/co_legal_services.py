from ..base import UrgentNeedFunction


class CoLegalServices(UrgentNeedFunction):
    dependencies = ["income_amount", "income_frequency", "household_size", "age"]
    max_age = 60

    def eligible(self):
        """
        Return True if the household is has an income bellow 200% FPL or someone in the household is over 60 years old
        """
        fpl = self.urgent_need.year.as_dict()
        is_income_eligible = self.screen.calc_gross_income("yearly", ["all"]) < fpl[self.screen.household_size]
        is_age_eligible = self.screen.num_adults(age_max=self.max_age) > 0
        main_eligibility = is_age_eligible or is_income_eligible
        has_rent_or_mortgage = self.screen.has_expense(["rent", "mortgage"])
        # don't apply the rent/mortgage condition to legal services need
        rent_mortgage_eligible = has_rent_or_mortgage or self.screen.needs_legal_services

        return main_eligibility and rent_mortgage_eligible
