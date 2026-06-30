from programs.programs.warnings.base import WarningCalculator


class SnapStudentWarning(WarningCalculator):
    dependencies = [
        "age",
    ]

    def eligible(self) -> bool:
        for member in self.screen.household_members.all():
            if not member.student:
                continue
            if member.age < 18 or member.age >= 50:
                continue
            if member.has_disability():
                continue
            if (member.is_head() or member.is_spouse()) and self.screen.num_children(age_max=5) > 0:
                continue
            if member.is_head() and not member.is_married()["is_married"] and self.screen.num_children(age_max=11) > 0:
                continue
            if self.screen.has_base_benefit("tanf"):
                continue
            if member.student_has_work_study or member.student_works_20_plus_hrs:
                continue
            if member.student_full_time is False:
                continue
            return True

        return False
