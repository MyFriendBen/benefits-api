from ..base import UrgentNeedFunction


class MassHealthApplication(UrgentNeedFunction):
    """
    CEOC - MassHealth Application Assistance

    Helps residents apply for free or low-cost health insurance.
    """

    dependencies = []

    def eligible(self) -> bool:

        # Check eligibility for MassHealth
        is_masshealth_eligible = any(
            program.get("name_abbreviated") == "ma_mass_health" and program.get("eligible")
            for program in (self.data or [])
        )

        return is_masshealth_eligible
