from ..base import UrgentNeedFunction


class NorthTexasFoodBank(UrgentNeedFunction):
    """
    North Texas Food Bank (NTFB) – Food Assistance & Mobile Pantries

    Regional food bank serving Dallas/North Texas with free food pantries,
    mobile distributions, and SNAP application help.

    Eligible counties: Collin, Dallas, Delta, Denton, Ellis, Fannin, Grayson,
    Hopkins, Hunt, Kaufman, Lamar, Navarro, Rockwall.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Eligibility varies — county restriction managed via admin configuration
        return True
