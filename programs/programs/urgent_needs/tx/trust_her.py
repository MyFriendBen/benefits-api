from ..base import UrgentNeedFunction


class TrustHer(UrgentNeedFunction):
    """
    Trust Her

    Free or low-cost birth control and reproductive health services for Dallas women
    and teens, with same-day access to all contraception methods.

    Dallas County ZIP code (county restriction managed via admin); 250% FPL or less;
    at least one household member has no health insurance.
    """

    dependencies = ["income_amount", "income_frequency", "household_size", "health_insurance"]
    fpl_percent = 2.5

    def eligible(self) -> bool:
        if self.urgent_need.year is None:
            return False

        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.urgent_need.year.get_limit(self.screen.household_size) * self.fpl_percent)

        if income > income_limit:
            return False

        return self.screen.has_insurance_types(["none"])
