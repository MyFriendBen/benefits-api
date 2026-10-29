from ..base import UrgentNeedFunction
from programs.programs.shared.program_results import eligible_in_results


class SNAPApplicationAssistance(UrgentNeedFunction):
    dependencies = ["county"]

    def eligible(self) -> bool:
        """
        CEOC - SNAP Application Assistance
        Free help applying for SNAP food benefits.

        Eligibility:
        -Up to 200% FPL (gross)
        -Must meet MA SNAP rules
        -Cambridge resident
        """

        # Condition 1: Cambridge residents --managed by admin panel

        # Condition 2: Not receiving SNAP
        has_snap = self.screen.has_benefit("ma_snap")
        if has_snap:
            return False

        # Condition 3: SNAP Eligible
        return eligible_in_results(self.data, "ma_snap")
