from ..base import UrgentNeedFunction


class CrossroadsCommunitySvcs(UrgentNeedFunction):
    """
    Crossroads Community Services

    Addresses food insecurity through an in-house community market and curbside
    ordering, serving families in Dallas, Ellis, and Navarro counties with emphasis
    on nutrition equity and family support.

    Counties: Dallas, Ellis, Navarro.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Residents of Dallas, Ellis, or Navarro counties — county restriction managed via admin configuration
        return True
