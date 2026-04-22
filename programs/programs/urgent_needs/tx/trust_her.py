from ..base import UrgentNeedFunction


class TrustHer(UrgentNeedFunction):
    """
    Trust Her

    Provides free or low-cost birth control and reproductive health services to Dallas
    women and teens, with same-day access to all contraception methods and enrollment
    support for Medicaid and coverage programs.

    Dallas County; women and teens; no age minimum; free or low cost based on income.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; women and teens — county restriction managed via admin configuration
        return True
