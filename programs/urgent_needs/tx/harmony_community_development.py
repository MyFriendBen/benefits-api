from ..base import UrgentNeedFunction


class HarmonyCommunityDevelopment(UrgentNeedFunction):
    """
    Harmony Community Development Corporation

    A nonprofit serving South Oak Cliff and southern suburbs offering rent assistance,
    legal aid, financial planning, and self-sufficiency programs including the H.E.L.P.
    program for unemployed/underemployed adults.

    Dallas County; South Oak Cliff and southern Dallas suburb residents.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; eligibility varies — county restriction managed via admin configuration
        return True
