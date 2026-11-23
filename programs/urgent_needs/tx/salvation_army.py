from ..base import UrgentNeedFunction


class SalvationArmy(UrgentNeedFunction):
    """
    Salvation Army Texas – Emergency Rent/Utility Help

    Local Salvation Army centers provide short-term rent and utility assistance
    for families in crisis when funds are available.

    All TX counties; rent expense required; eligibility varies.
    Required expense (rent) managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # All TX counties; eligibility varies — required expense managed via admin configuration
        return True
