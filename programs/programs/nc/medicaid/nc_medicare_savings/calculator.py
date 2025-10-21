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
        - If any household member has SSI → that person is excluded from income & household count
        """
        has_ssi = member.calc_gross_income("yearly", ["sSI"]) > 0
        e.condition(not has_ssi)
        if has_ssi:
            return

        # Check spouse SSI
        spouse_ssi = spouse.calc_gross_income("yearly", ["sSI"]) if spouse else 0

        # Case 2: collect household members and exclude SSI recipients
        household = list(self.screen.household_members.all())
        excluded_members = [m for m in household if m.calc_gross_income("yearly", ["sSI"]) > 0]

        # exclude SSI recipients from income and adjust household size
        included_members = [m for m in household if m not in excluded_members]
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

        if countable_income is not None and min_income is not None:
            e.condition(countable_income >= min_income)
        else:
            e.condition(False)
        if countable_income is not None and max_income is not None:
            e.condition(countable_income <= max_income)
        else:
            e.condition(False)
