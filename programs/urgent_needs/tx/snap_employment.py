from ..base import UrgentNeedFunction
from programs.programs.shared.program_results import has_or_is_eligible_for


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
        return has_or_is_eligible_for(self.screen, self.data, "tx_snap")
