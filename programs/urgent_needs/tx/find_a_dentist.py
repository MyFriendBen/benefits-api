from ..base import UrgentNeedFunction


class FindADentist(UrgentNeedFunction):
    """
    Find a Dentist (Texas DSHS)

    State directory guiding residents to free/low-cost dental clinics and programs.

    All TX counties; eligibility varies.
    """

    dependencies = []

    def eligible(self) -> bool:
        # All TX counties; eligibility varies — managed via admin configuration
        return True
