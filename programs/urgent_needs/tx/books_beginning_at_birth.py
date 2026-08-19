from ..base import UrgentNeedFunction


class BooksBeginningAtBirth(UrgentNeedFunction):
    """
    Books Beginning at Birth

    A statewide family literacy program providing free print books twice yearly to
    Texas families with children birth to age 4, plus access to a digital library
    with hundreds of age-appropriate books and literacy activities.

    Dallas County; Texas families with children ages 0–4.
    County restriction managed via admin configuration.
    """

    dependencies = ["age"]
    max_age = 4

    def eligible(self) -> bool:
        # Must have a child 4 years old or younger
        return self.screen.num_children(age_max=self.max_age) > 0
