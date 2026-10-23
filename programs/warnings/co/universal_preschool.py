from programs.warnings.base import WarningCalculator


class UniversalPreschool(WarningCalculator):
    dependencies = [
        "age",
    ]
    # Reads eligibility.member_verdicts below, so it can only be evaluated during a
    # real eligibility run — not from a snapshot. See WarningCalculator.
    needs_full_eligibility = True
    age = 3

    def eligible(self) -> bool:
        for member_eligibility in self.eligibility.member_verdicts:
            if member_eligibility.eligible and member_eligibility.member.calc_age() == 3:
                return True

        return False
