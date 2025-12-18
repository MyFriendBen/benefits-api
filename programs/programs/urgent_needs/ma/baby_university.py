from ..base import UrgentNeedFunction


class BabyUniversity(UrgentNeedFunction):
    """
    Baby University (Baby U)

    Free classes and support for parents/caregivers of babies and toddlers.
    Cambridge city program; families with children 3 and younger. Cohort-based with limited spots.
    """

    dependencies = ["age"]
    max_age = 3

    def eligible(self):
        # Must have a child 3 years old or younger
        return self.screen.num_children(age_max=self.max_age) > 0
