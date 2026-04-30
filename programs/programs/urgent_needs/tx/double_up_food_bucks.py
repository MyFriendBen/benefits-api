from ..base import UrgentNeedFunction


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
        if self.screen.has_benefit("tx_snap"):
            return True

        for program in self.data or []:
            if not isinstance(program, dict):
                continue
            if program.get("name_abbreviated") == "tx_snap" and program.get("eligible"):
                return True

        return False
