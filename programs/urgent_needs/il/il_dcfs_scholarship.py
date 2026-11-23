from ..base import UrgentNeedFunction


class IlDcfsScholarship(UrgentNeedFunction):
    """
    Illinois DCFS Scholarship (additional resource).

    Shown when a household member who is a student has foster care history. Selection is
    competitive (school record, activities, recommendation letters, an essay), so it is a
    resource rather than a computed program, and none of that is screened.

    Deliberately not gated on age (no published ceiling) or income (not income-tested).
    The Illinois white label stands in for the state of care.

    A member counts as having foster care history when any of these is true:
      - they ticked the "Ever in foster care, even briefly" tile;
      - they are listed as a foster child ("Foster Child / Kinship Care").
    """

    dependencies = ["relationship", "student"]

    def eligible(self) -> bool:
        return any(
            member.student is True and (member.was_in_foster_care is True or member.relationship == "fosterChild")
            for member in self.screen.household_members.all()
        )
