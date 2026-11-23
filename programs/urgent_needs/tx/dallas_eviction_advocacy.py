from ..base import UrgentNeedFunction


class DallasEvictionAdvocacy(UrgentNeedFunction):
    """
    Dallas Eviction Advocacy Center

    Provides pro bono legal advice and representation to all Dallas County tenants
    facing eviction, regardless of income, race, immigration status, or native language.

    Dallas County; no income limit.
    Required expense (rent) managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County tenants facing eviction; no income limit
        # Required expense (rent) and county restriction managed via admin configuration
        return True
