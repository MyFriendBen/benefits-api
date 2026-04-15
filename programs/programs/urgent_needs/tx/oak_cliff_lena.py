from ..base import UrgentNeedFunction


class OakCliffLena(UrgentNeedFunction):
    """
    For Oak Cliff Language Environment Program (LENA)

    A 10-week family engagement program helping parents increase quality conversations
    with young children using personalized feedback and a word-count tracking device,
    plus books and resources for building early literacy.

    Dallas County; Oak Cliff families with children ages 2 months to 5 years.
    County restriction managed via admin configuration.
    """

    dependencies = ["age"]
    max_age = 4

    def eligible(self) -> bool:
        # Must have a child under 5 years old
        return self.screen.num_children(age_max=self.max_age) > 0
