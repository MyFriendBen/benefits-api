from ..base import UrgentNeedFunction


class AffordableHousingServices(UrgentNeedFunction):
    """
    Just a Start – Affordable Housing Services

    Helps residents access affordable rental and homeownership opportunities.
    Cambridge priority; housing-need based. Income varies by housing program (AMI-based).
    """

    dependencies = []

    def eligible(self):
        # All users selecting housing as acute condition are eligible
        # Specific eligibility (Cambridge residency, housing instability) managed via admin configuration
        return True
