from ..base import UrgentNeedFunction


class GroceryClearanceOutlet(UrgentNeedFunction):
    """
    Grocery Clearance Outlet

    A surplus and salvage grocery store offering name-brand products at approximately
    50% off retail prices, specializing in overstock and manufacturer excess goods
    for budget-conscious shoppers.

    Dallas County; no specific eligibility requirements.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; no eligibility requirements — county restriction managed via admin configuration
        return True
