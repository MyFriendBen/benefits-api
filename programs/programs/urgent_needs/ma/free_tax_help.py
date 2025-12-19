from ..base import UrgentNeedFunction


class FreeTaxHelp(UrgentNeedFunction):
    """
    CEOC – Free Tax Help (VITA)
    Free tax preparation to help residents file returns and claim credits.
    Cambridge resident or income-eligible. Generally ≤ $60,000 annual income

    """

    dependencies = ["county", "income_amount", "income_frequency"]
    eligible_city = "Cambridge"
    income_limit = 60000

    def eligible(self):

        # Condition 1: Cambridge residents
        is_cambridge = self.screen.county == self.eligible_city

        # Condition 1: Cambridge residents
        income = self.screen.calc_gross_income("yearly", ["all"])
        is_income_eligible = income <= self.income_limit

        return is_cambridge or is_income_eligible
