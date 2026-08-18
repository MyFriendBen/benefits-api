from ..base import UrgentNeedFunction


# Catastrophic Illness in Children Relief Fund
class Cicrf(UrgentNeedFunction):
    dependencies = ["age"]
    max_age = 21

    def eligible(self):
        # Condition 1: Household needs child development help
        needs_child_help = self.screen.needs_child_dev_help

        # Condition 2:  Household has kids
        has_child = self.screen.num_children(age_max=self.max_age, include_pregnant=True) > 0

        return needs_child_help and has_child
