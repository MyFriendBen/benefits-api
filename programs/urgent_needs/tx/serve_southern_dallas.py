from ..base import UrgentNeedFunction


class ServeSouthernDallas(UrgentNeedFunction):
    """
    Serve Southern Dallas – Diaper Day / Emergency Diaper Assistance

    Coordinates monthly diaper distributions and emergency diaper support
    for families in South Dallas.

    Counties: Dallas, Ellis, Navarro.
    Must have a child under 5 years old and need baby supplies.
    County restriction managed via admin configuration.
    """

    dependencies = ["age"]
    max_age = 4

    def eligible(self) -> bool:
        has_young_child = self.screen.num_children(age_max=self.max_age) > 0
        has_needs_baby_supplies = bool(self.screen.needs_baby_supplies)
        return has_young_child and has_needs_baby_supplies
