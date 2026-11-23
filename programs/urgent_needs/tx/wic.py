from ..base import UrgentNeedFunction


class Wic(UrgentNeedFunction):
    """
    WIC / Farmers Market Nutrition Program

    WIC provides supplemental foods, healthcare referrals, and nutrition education
    for low-income pregnant, breastfeeding, and postpartum women, and infants and
    children up to age 5. The Farmers Market Nutrition Program provides vouchers
    to buy fresh produce at authorized farmers markets.

    Must be pregnant, postpartum, breastfeeding, infant, or child under 5;
    income-based eligibility.
    County restriction managed via admin configuration.
    """

    dependencies = ["age"]
    max_age = 4

    def eligible(self) -> bool:
        # Eligible if there is a child under 5 or a pregnant household member
        return self.screen.num_children(age_max=self.max_age, include_pregnant=True) > 0
