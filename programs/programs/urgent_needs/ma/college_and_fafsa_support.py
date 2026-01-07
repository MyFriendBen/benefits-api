from ..base import UrgentNeedFunction


class CollegeAndFafsaSupport(UrgentNeedFunction):
    """
    CEOC - College & FAFSA Support
    Helps students complete FAFSA and access college financial aid.
    Cambridge resident or student. No income limit; affects aid eligibility.
    """

    dependencies = ["county", "student"]
    eligible_city = "Cambridge"

    def eligible(self) -> bool:
        # Condition 1:  Cambridge residents
        is_cambridge = self.screen.county == self.eligible_city

        # Condition 2:  Student
        is_student = self.screen.household_members.filter(student=True).exists()

        return is_cambridge or is_student
