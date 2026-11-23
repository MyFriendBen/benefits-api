from ..base import UrgentNeedFunction


class LegalAidNorthwestTexas(UrgentNeedFunction):
    """
    Legal Aid of NorthWest Texas

    Provides free civil legal services to low-income individuals and families in
    North Texas, covering issues including family law, housing, consumer protection,
    and public benefits.

    Dallas County; income-based eligibility (contact organization for income guidelines).
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; income-based eligibility — county restriction managed via admin configuration
        return True
