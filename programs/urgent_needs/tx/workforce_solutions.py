from ..base import UrgentNeedFunction


class WorkforceSolutions(UrgentNeedFunction):
    """
    Texas Workforce Commission - Job Training / Workforce Solutions

    Offers job search support, training programs, and career services through local Workforce Solutions offices.
    All TX counties and eligibility varies
    """

    dependencies = []

    def eligible(self) -> bool:
        # All users selecting job resources are eligible
        return True
