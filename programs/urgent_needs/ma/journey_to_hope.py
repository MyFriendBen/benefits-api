from ..base import UrgentNeedFunction


class JourneyToHopeCEOC(UrgentNeedFunction):
    dependencies = []

    def eligible(self):
        """
        Journey to Hope (CEOC)
        Provides short-term financial help and case management during crises.
        """

        # Eligibility is managed via the admin portal (Cambridge residency and mental health category selection).

        return True
