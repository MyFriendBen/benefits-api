from ..base import UrgentNeedFunction


class MassHealthApplication(UrgentNeedFunction):
    """
    CEOC - MassHealth Application Assistance

    Helps residents apply for free or low-cost health insurance.
    """

    dependencies = []

    def eligible(self):

        # Condition 1: Not having MassHealth
        has_masshealth = any(member.insurance.mass_health for member in self.screen.household_members.all())

        # Condition 2: Eligible for MassHealth
        is_masshealth_eligible = any(
            program["name_abbreviated"] == "ma_mass_health" and program["eligible"] for program in self.data
        )

        return is_masshealth_eligible and not has_masshealth
