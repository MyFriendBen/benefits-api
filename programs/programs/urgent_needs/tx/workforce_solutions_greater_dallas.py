from ..base import UrgentNeedFunction


class WorkforceSolutionsGreaterDallas(UrgentNeedFunction):
    """
    Workforce Solutions Greater Dallas

    Provides free employment services including job search assistance, resume help,
    skills training, and connections to employer job openings for Dallas-area job seekers.

    Dallas County; Dallas area residents seeking employment.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; no eligibility requirements — county restriction managed via admin configuration
        return True
