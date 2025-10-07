from programs.programs.calc import MemberEligibility
from programs.programs.federal.medicare_savings.calculator import MedicareSavings
from typing import ClassVar


class MedicareSavingsNC(MedicareSavings):
    ineligible_insurance_types: ClassVar[tuple[str, ...]] = ("va", "medicaid")
    asset_limit: ClassVar[dict[str, int]] = {"single": 9_660, "married": 14_470}
    min_income_percent: ClassVar[float] = 1.0

    def member_eligible(self, e: MemberEligibility):
        super().member_eligible(e)
        member = e.member

        # NC-specific: not on benefits
        e.condition(not self.screen.has_benefit("aca"))
        e.condition(not self.screen.has_benefit("medicaid"))

        # insurance
        e.condition(not member.insurance.has_insurance_types(self.ineligible_insurance_types))

        # recompute income using NC-specific thresholds (no SSI)
        status, spouse = self.get_marital_status(member)
        earned, unearned, _ = self.get_combined_income(member, spouse, include_ssi=False)
        earned, unearned = self.apply_income_disregards(earned, unearned)
        countable_income = earned + unearned

        min_income, max_income = self.get_fpl_limits(self.screen.household_size, self.min_income_percent)

        if countable_income is not None and min_income is not None:
            e.condition(countable_income >= min_income)
        else:
            e.condition(False)
        if countable_income is not None and max_income is not None:
            e.condition(countable_income <= max_income)
        else:
            e.condition(False)
