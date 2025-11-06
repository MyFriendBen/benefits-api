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
        e.condition(not self.screen.has_benefit("nc_aca"))
        e.condition(not self.screen.has_benefit("ssi"))
        e.condition(not self.screen.has_benefit("nc_medicare_savings"))

        # insurance
        e.condition(not member.insurance.has_insurance_types(self.ineligible_insurance_types))

    def check_income_limits(self, e: MemberEligibility, member, spouse):
        """
        NC-specific logic:
        - SSI is excluded from income
        - If member has SSI → automatically excluded (already qualifies for Medicaid/Medicare)
        - If any household member has SSI → that person is excluded from income & household count
        """
        # Case 1: the member themselves receives SSI → not eligible for Medicare Savings (gets full Medicare)
        has_ssi = member.calc_gross_income("yearly", ["sSI"]) > 0
        e.condition(not has_ssi)

        # Case 2: collect household members and exclude SSI recipients
        household = list(self.screen.household_members.all())
        included_members = [m for m in household if m.calc_gross_income("yearly", ["sSI"]) == 0]
        household_size = len(included_members)

        # compute combined income (excluding SSI)
        earned_total = 0
        unearned_total = 0
        for m in included_members:
            earned, unearned, _ = self.get_combined_income(m, spouse=None, include_ssi=False)
            earned_total += earned
            unearned_total += unearned

        earned_total, unearned_total = self.apply_income_disregards(earned_total, unearned_total)
        countable_income = earned_total + unearned_total

        min_income, max_income = self.get_fpl_limits(household_size, self.min_income_percent)

        e.condition(min_income is not None and countable_income >= min_income)
        e.condition(max_income is not None and countable_income <= max_income)
