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
        - If member has SSI → automatically excluded (skip check)
        - If spouse has SSI → exclude spouse's SSI from income
        """
        if member.calc_gross_income("yearly", ["sSI"]) > 0:
            # They already qualify for Medicaid/Medicare Savings via SSI
            e.condition(False)
            return

        spouse_ssi = 0
        if spouse:
            spouse_ssi = spouse.calc_gross_income("yearly", ["sSI"])

        if spouse and spouse_ssi > 0:
            earned, unearned, _ = self.get_combined_income(member, spouse=None, include_ssi=False)
        else:
            earned, unearned, _ = self.get_combined_income(member, spouse, include_ssi=False)

        earned, unearned = self.apply_income_disregards(earned, unearned)
        countable_income = earned + unearned

        household_size = 1 if spouse_ssi > 0 else self.screen.household_size
        min_income, max_income = self.get_fpl_limits(household_size, self.min_income_percent)

        if countable_income is not None and min_income is not None:
            e.condition(countable_income >= min_income)
        else:
            e.condition(False)
        if countable_income is not None and max_income is not None:
            e.condition(countable_income <= max_income)
        else:
            e.condition(False)
