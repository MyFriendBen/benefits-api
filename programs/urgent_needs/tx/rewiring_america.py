from ..base import UrgentNeedFunction


class RewiringAmerica(UrgentNeedFunction):
    """
    Rewiring America

    Rewiring America has a tool that can help you save money on electric appliances.
    You can use this tool to find tax credits, rebates, and discounts. You may also save money on an electric vehicle.

    All TX counties, eligibility varies and required expense is Other Utilities
    """

    dependencies = []

    def eligible(self) -> bool:
        # All TX users selecting help with housing utilities(other utilities) are eligible
        # Specific eligibility (required expense) managed via admin configuration
        return True
