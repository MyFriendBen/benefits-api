from ..base import UrgentNeedFunction


class ForeclosureFinAssistProgram(UrgentNeedFunction):
    dependencies = ["household_size", "income_amount", "income_frequency", "county"]
    income_limits = {
        1: 66_300,
        2: 75_750,
        3: 85_200,
        4: 94_560,
        5: 102_250,
        6: 109_800,
        7: 117_400,
        8: 124_950,
    }

    def eligible(self):
        """
        Return True if the household is at or below 80% the income limit for their household size & they live in Denver
        """
        household_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.income_limits[self.screen.household_size]
        has_mortgage = self.screen.has_expense(["mortgage"])
        return household_income <= income_limit and self.screen.county == "Denver County" and has_mortgage
