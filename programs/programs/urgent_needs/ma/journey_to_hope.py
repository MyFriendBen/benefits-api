from ..base import UrgentNeedFunction

class JourneyToHopeCEOC(UrgentNeedFunction):
    dependencies = ["county"]
    eligible_city = "Cambridge"

    def eligible(self):
        """
        Journey to Hope (CEOC) 	
        Provides short-term financial help and case management during crises.
        """
        # Cambridge resident
        is_cambridge = self.screen.county == self.eligible_city

        return is_cambridge