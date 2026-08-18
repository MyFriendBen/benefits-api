from ..base import UrgentNeedFunction


class FindFoodIl(UrgentNeedFunction):
    """
    Find Food IL

    Use the Find Food IL map to find free food or meals near you.

    Must have a child under 22 years old and household income less than $22k/year.
    County and required expense restrictions managed via admin configuration.
    """

    dependencies = ["age", "income_amount", "income_frequency"]
    income_limit = 22_000
    max_child_age = 21

    def eligible(self) -> bool:
        has_young_member = self.screen.num_children(age_max=self.max_child_age) > 0
        income = self.screen.calc_gross_income("yearly", ["all"])
        return has_young_member and income <= self.income_limit
