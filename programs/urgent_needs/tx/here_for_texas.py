from ..base import UrgentNeedFunction


class HereForTexas(UrgentNeedFunction):
    """
    Here For Texas

    Statewide mental health and addiction resource hub that explains options and helps people find local/virtual care.
    """

    dependencies = []

    def eligible(self) -> bool:
        # All TX counties; eligibility varies
        return True
