from ..base import UrgentNeedFunction


class OakCliffVeggieProject(UrgentNeedFunction):
    """
    Oak Cliff Veggie Project

    A nonprofit that increases access to fresh produce through cooperative growing
    spaces and community education, operating a veggie store serving 1,000+ families
    monthly and managing community garden spaces in food deserts.

    Dallas County; Oak Cliff and surrounding food desert area residents.
    County restriction managed via admin configuration.
    """

    dependencies = []

    def eligible(self) -> bool:
        # Dallas County; eligibility varies — county restriction managed via admin configuration
        return True
