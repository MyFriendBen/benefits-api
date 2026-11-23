from ..base import UrgentNeedFunction


class LivesInDenver(UrgentNeedFunction):
    dependencies = ["county"]
    county = "Denver County"

    def eligible(self):
        """
        Household lives in the Denver County
        """
        return self.screen.county == self.county


class ChildAgeFunction(UrgentNeedFunction):
    dependencies = ["age"]
    min_age = 0
    max_age = 18

    def eligible(self):
        """
        return True if the child is between the ages of min_age and max_age
        """
        return self.screen.num_children(age_min=self.min_age, age_max=self.max_age) > 0


class Child(ChildAgeFunction):
    pass


class HasRentOrMortgage(UrgentNeedFunction):
    def eligible(self):
        """
        Return True if rent or mortgage is listed as an expense
        """
        has_rent_or_mortgage = self.screen.has_expense(["rent", "mortgage"])

        return has_rent_or_mortgage
