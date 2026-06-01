from ..base import UrgentNeedFunction


class FirstStepStaffing(UrgentNeedFunction):
    """
    First Step Staffing

    Places job seekers facing barriers to employment with Dallas-area employers
    and provides wraparound support including transportation, job readiness
    coaching, workplace communication support, and long-term retention services.

    Dallas County; no code-level eligibility requirements.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        return True
