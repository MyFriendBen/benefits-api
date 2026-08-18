from ..base import UrgentNeedFunction


class WestDallasMultipurposeCenter(UrgentNeedFunction):
    """
    West Dallas Multipurpose Center

    A city facility offering free programs in education, health and wellness,
    senior services, and community engagement, plus financial assistance including
    rental assistance, utility payments, and security deposit help.

    Dallas County; West Dallas residents.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; West Dallas residents — county restriction managed via admin configuration
        return True
