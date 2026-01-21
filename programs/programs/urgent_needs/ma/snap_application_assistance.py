from ..base import UrgentNeedFunction


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

        # Condition 3: SNAP Eligible
        is_snap_eligible = False

        for program in self.data or []:
            if not isinstance(program, dict):
                continue

            if program.get("name_abbreviated") != "ma_snap":
                continue

            if program.get("eligible"):
                is_snap_eligible = True
                break

        return is_snap_eligible and not has_snap
