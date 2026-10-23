from ..base import UrgentNeedFunction
from programs.programs.shared.program_results import eligible_in_results


class MassHealthApplication(UrgentNeedFunction):
    """
    CEOC - MassHealth Application Assistance

    Helps residents apply for free or low-cost health insurance.
    """

    dependencies = []

    def eligible(self) -> bool:
        return eligible_in_results(self.data, "ma_mass_health")
