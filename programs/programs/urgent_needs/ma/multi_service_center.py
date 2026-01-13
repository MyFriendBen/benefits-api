from ..base import UrgentNeedFunction


class MultiServiceCenter(UrgentNeedFunction):
    """
    Multi-Service Center (Homelessness & Eviction-Prevention Services)

    Housing stability help for Cambridge residents, including eviction prevention support and connections to resources.
    """

    dependencies = []

    def eligible(self):
        # All users selecting housing as acute condition are eligible
        # Specific eligibility (Cambridge residency, housing instability) managed via admin configuration
        return True
