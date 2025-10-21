from programs.programs.calc import MemberEligibility
from programs.programs.federal.medicare_savings.calculator import MedicareSavings
from typing import ClassVar


class MedicareSavingsNC(MedicareSavings):
    ineligible_insurance_types: ClassVar[tuple[str, ...]] = ("va", "medicaid")
    asset_limit: ClassVar[dict[str, int]] = {"single": 9_660, "married": 14_470}
    min_income_percent: ClassVar[float] = 1.0

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        super().member_eligible(e)

        # NC-specific: not on benefits
        e.condition(not self.screen.has_benefit("aca"))
        e.condition(not self.screen.has_benefit("medicaid"))

        # insurance
        e.condition(not member.insurance.has_insurance_types(self.ineligible_insurance_types))

    def check_income_limits(self, e: MemberEligibility, member, spouse):
        """
        NC-specific logic:
        - SSI is excluded from income
        - If member has SSI → automatically excluded (already qualifies for Medicaid/Medicare)
        - If spouse has SSI → exclude spouse entirely and reduce household size by 1
        """
        has_ssi = member.calc_gross_income("yearly", ["sSI"]) > 0
        e.condition(not has_ssi)
        if has_ssi:
            return

        # Check spouse SSI
        spouse_ssi = spouse.calc_gross_income("yearly", ["sSI"]) if spouse else 0

        # If spouse has SSI, exclude spouse entirely
        if spouse and spouse_ssi > 0:
            earned, unearned, _ = self.get_combined_income(member, spouse=None, include_ssi=False)
        else:
            earned, unearned, _ = self.get_combined_income(member, spouse, include_ssi=False)

        earned, unearned = self.apply_income_disregards(earned, unearned)
        countable_income = earned + unearned

        household_size = self.screen.household_size or 0
        if spouse_ssi > 0 and household_size > 1:
            household_size -= 1

        min_income, max_income = self.get_fpl_limits(household_size, self.min_income_percent)

        if countable_income is not None and min_income is not None:
            e.condition(countable_income >= min_income)
        else:
            e.condition(False)
        if countable_income is not None and max_income is not None:
            e.condition(countable_income <= max_income)
        else:
            e.condition(False)
