from ..base import UrgentNeedFunction


class DoMoreGoodStore(UrgentNeedFunction):
    """
    Do More Good Store (Volunteer Now)

    VolunteerNow connects volunteers with nonprofits across Dallas County in education,
    health, hunger relief, and other causes; the Do More Good Store supports their
    mission and community impact.

    Dallas County; no specific eligibility requirements.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; no eligibility requirements — county restriction managed via admin configuration
        return True
