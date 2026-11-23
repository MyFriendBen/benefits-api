from ..base import UrgentNeedFunction


class MealInCounties(UrgentNeedFunction):
    dependencies = ["county"]

    def eligible(self):
        """
        MEAL (Additional Resource for food) eligibility function.

        Eligibility is ONLY determined by county, which is handled by the base
        UrgentNeedFunction class county_eligible() method using counties
        configured in the Django admin (UrgentNeed.counties field).

        Returns True to indicate no additional eligibility checks are needed.
        Note: If no counties are selected in admin, MEAL will be available to
        all counties.
        """
        return True
