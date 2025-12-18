from ..base import UrgentNeedFunction


class CareerTrainingAndWorkforce(UrgentNeedFunction):
    dependencies = ["age", "income_amount", "income_frequency", "household_size", "needs_job_resources"]
    min_age = 18
    fpl_percent = 2

    def eligible(self):
        """
        Career Training and Workforce Development
        Programs and services to help individuals gain skills and find employment.
        """

        # Condition 1: Individual is 18+
        is_adult = self.screen.num_adults(age_max=self.min_age) > 0

        # Condition 2: income less than 200% FPL
        # income_limit = self.urgent_need.year.as_dict()[self.screen.household_size] * self.fpl_percent
        income_limit = int(self.urgent_need.year.get_limit(self.screen.household_size) * self.fpl_percent)
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_eligible = income <= income_limit

        # Condition 3: Household needs job resources
        needs_job_resources = self.screen.needs_job_resources

        return is_adult and income_eligible and needs_job_resources
