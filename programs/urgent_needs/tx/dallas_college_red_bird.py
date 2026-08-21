from ..base import UrgentNeedFunction


class DallasCollegeRedBird(UrgentNeedFunction):
    """
    Dallas College Red Bird Workforce Training Center

    Offers short-term workforce training programs, continuing education, and career
    development courses at the Red Bird campus to help residents gain job-ready skills
    in high-demand fields.

    Dallas County; open enrollment, some programs may have income-based assistance.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; open enrollment — county restriction managed via admin configuration
        return True
