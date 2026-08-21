from ..base import UrgentNeedFunction


class SnapEmploymentTraining(UrgentNeedFunction):
    """
    SNAP Employment & Training (SNAP E&T) – TWC

    Employment, training, and support services specifically for people receiving SNAP
    to help them get higher-paying work.

    All TX counties; must be receiving SNAP benefits.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Must be receiving SNAP benefits
        if self.screen.has_benefit("tx_snap"):
            return True

        for program in self.data or []:
            if not isinstance(program, dict):
                continue
            if program.get("name_abbreviated") == "tx_snap" and program.get("eligible"):
                return True

        return False
