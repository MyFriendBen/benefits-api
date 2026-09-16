from programs.warnings.base import WarningCalculator


class UniversalPreschool(WarningCalculator):
    dependencies = [
        "age",
    ]
    # Reads eligibility.eligible_members below, so it can only be evaluated during a
    # real eligibility run — not from a snapshot. See WarningCalculator.
    needs_full_eligibility = True
    age = 3

    def eligible(self) -> bool:
        for member_eligibility in self.eligibility.eligible_members:
            if member_eligibility.eligible and member_eligibility.member.age == 3:
                return True

        return False
