from ..base import UrgentNeedFunction


class CenterForFamilies(UrgentNeedFunction):
    """
    Center for Families (Birth–8 Parenting Education & Support)
    Free parenting support, playgroups, workshops, and referrals for families with young children in Cambridge.
    """

    dependencies = ["age"]
    max_age = 8

    def eligible(self) -> bool:
        # Provides parenting education and support programs for Cambridge families with children from birth to age 8.

        # Must have a child 8 years old or younger
        return self.screen.num_children(age_max=self.max_age) > 0
