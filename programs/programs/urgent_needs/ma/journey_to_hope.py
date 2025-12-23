from ..base import UrgentNeedFunction


class JourneyToHopeCEOC(UrgentNeedFunction):
    dependencies = []

    def eligible(self):
        """
        Journey to Hope (CEOC)
        Provides short-term financial help and case management during crises.
        """

        # Specific eligibility (Cambridge residency) managed via admin configuration
        # This program should appear for those who selected mental health on Additional Resources step

        return True
