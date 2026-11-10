from ..base import UrgentNeedFunction
from programs.programs.shared.program_results import has_or_is_eligible_for


class DoubleUpFoodBucks(UrgentNeedFunction):
    """
    Double Up Food Bucks (DUFB)

    Doubles the value of SNAP/EBT dollars when used to purchase fresh fruits
    and vegetables at participating Texas farmers markets and grocery stores.

    SNAP/EBT card required.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Must have or be eligible for SNAP
        return has_or_is_eligible_for(self.screen, self.data, "tx_snap")
