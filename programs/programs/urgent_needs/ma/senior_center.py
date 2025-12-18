from ..base import UrgentNeedFunction


class CambridgeSeniorCenter(UrgentNeedFunction):
    dependencies = ["age", "county", "needs_legal_services"]
    min_age = 60
    eligible_city = "Cambridge"

    def eligible(self):
        """
        Cambridge Senior Center (Council on Aging Programs)
        Free or low-cost activities, support groups, and services for older adults, plus meals and tech help.
        Some services (meals, tech help) may require reservations/appointments.

        Eligibility:
        - Age: 60+
        - Location: Cambridge residents
        - Needs: Legal services
        """

        # Condition 1: Household needs legal services
        needs_legal_help = self.screen.needs_legal_services

        # Condition 2:  Cambridge residents age 60+.
        is_senior = self.screen.num_adults(age_max=self.min_age) > 0
        is_cambridge = self.screen.county == self.eligible_city

        return is_senior and is_cambridge and needs_legal_help
