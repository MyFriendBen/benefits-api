from ..base import UrgentNeedFunction


class ClaimItTexas(UrgentNeedFunction):
    """
    Claimittexas.gov

    Free state tool to search for and claim unclaimed property held by Texas,
    such as forgotten bank accounts, insurance payouts, utility deposits,
    and other funds reported to the Texas Comptroller.

    All TX counties; documentation required.
    """

    dependencies = []

    def eligible(self) -> bool:
        # All TX counties; documentation required — no automated eligibility check
        return True
