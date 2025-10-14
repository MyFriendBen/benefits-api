from programs.programs.calc import MemberEligibility, ProgramCalculator
from typing import ClassVar


class MedicareSavings(ProgramCalculator):
    eligible_insurance_types = ("none", "employer", "private", "medicare")
    asset_limit = {
        "single": 11_160,
        "married": 17_470,
    }
    min_age = 65
    member_amount = 185 * 12
    general_income_disregard = 20 * 12
    earned_income_disregard = 65 * 12
    max_income_percent = 1.35
    dependencies: ClassVar[list[str]] = [
        "household_assets",
        "relationship",
        "income_frequency",
        "income_amount",
        "age",
        "insurance",
    ]

    def get_marital_status(self, member):
        is_married = member.is_married()
        return ("married" if is_married["is_married"] else "single"), is_married.get("married_to")

    def get_combined_income(self, member, spouse=None, include_ssi=True):
        earned = member.calc_gross_income("yearly", ["earned"])
        unearned = member.calc_gross_income("yearly", ["unearned"], ["sSI"] if include_ssi else [])
        ssi = member.calc_gross_income("yearly", ["sSI"]) if include_ssi else 0

        if spouse:
            earned += spouse.calc_gross_income("yearly", ["earned"])
            unearned += spouse.calc_gross_income("yearly", ["unearned"], ["sSI"] if include_ssi else [])
            if include_ssi:
                ssi += spouse.calc_gross_income("yearly", ["sSI"])

        return earned, unearned, ssi

    def apply_income_disregards(self, earned, unearned):
        if unearned >= self.general_income_disregard:
            unearned -= self.general_income_disregard
        else:
            remaining = self.general_income_disregard - unearned
            unearned = 0
            earned = max(0, earned - remaining)

        earned = max(0, earned - self.earned_income_disregard)
        earned /= 2
        return earned, unearned

    def get_fpl_limits(self, household_size, min_percent=None):
        fpl = self.program.year.as_dict()[household_size]
        min_income = fpl * min_percent if min_percent else None
        max_income = fpl * self.max_income_percent
        return min_income, max_income

    # ---------- main eligibility ----------
    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(member.age >= self.min_age)

        # insurance
        e.condition(member.insurance.has_insurance_types(self.eligible_insurance_types))

        # marital status & assets
        status, spouse = self.get_marital_status(member)
        e.condition(self.screen.household_assets <= self.asset_limit[status])

        # income limits check (federal logic)
        self.check_income_limits(e, member, spouse)

    def check_income_limits(self, e: MemberEligibility, member, spouse):
        """Default federal logic (includes SSI)."""
        earned, unearned, ssi = self.get_combined_income(member, spouse, include_ssi=True)
        earned, unearned = self.apply_income_disregards(earned, unearned)

        countable_income = earned + unearned + ssi

        _, max_income = self.get_fpl_limits(self.screen.household_size)
        e.condition(countable_income <= max_income)
