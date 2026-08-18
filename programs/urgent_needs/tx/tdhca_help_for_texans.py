from ..base import UrgentNeedFunction


class TdhcaHelpForTexans(UrgentNeedFunction):
    """
    TDHCA "Help for Texans" Housing & Eviction Resources

    State hub listing rental assistance, eviction help, public housing contacts,
    and emergency/homeless services.

    All TX counties; rent expense required; eligibility varies.
    Required expense (rent) managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # All TX counties; eligibility varies — required expense managed via admin configuration
        return True
