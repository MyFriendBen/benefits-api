from ..base import UrgentNeedFunction


class FeedingTexas(UrgentNeedFunction):
    """
    Feeding Texas

    Helps families locate their neariest local food bank by ZIP code,
    connecting them to free, nutritious food and meal programs.
    """

    dependencies = []

    def eligible(self) -> bool:
        # All TX counties; eligibility varies
        return True
