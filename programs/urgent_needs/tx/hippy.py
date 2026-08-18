from ..base import UrgentNeedFunction


class Hippy(UrgentNeedFunction):
    """
    HIPPY (Home Instruction for Parents of Preschool Youngsters)

    A home-based early education program that helps parents be their child's first
    teacher through curriculum packets and biweekly home visits or group meetings
    with a parent educator.

    Dallas County; families with children ages 3–5.
    County restriction managed via admin configuration.
    """

    dependencies = ["age"]
    min_age = 3
    max_age = 5

    def eligible(self) -> bool:
        # Must have a child between 3 and 5 years old
        return self.screen.num_children(age_min=self.min_age, age_max=self.max_age) > 0
