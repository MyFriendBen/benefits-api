from programs.programs.calc import MemberEligibility, ProgramCalculator
from screener.models import Insurance


class MedicareSavingsNC(ProgramCalculator):
    eligible_insurance_types = ("none", "employer", "private", "medicare")
    ineligible_insurance_types = ["va", "medicaid"]
    asset_limit = {"single": 9_660, "married": 14_470}
    min_age = 65
    min_income_percent = 1.0
    max_income_percent = 1.35
    member_amount = 185 * 12
    earned_income_disregard = 65 * 12 * 0.5
    general_income_disregard = 20 * 12

    dependencies = [
        "household_assets",
        "relationship",
        "income_frequency",
        "income_amount",
        "age",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(member.age >= self.min_age)

        # insurance
        e.condition(not self.screen.has_benefit("aca"))
        e.condition(not self.screen.has_benefit("medicaid"))

        e.condition(member.insurance.has_insurance_types(self.eligible_insurance_types))

        # assets
        is_married = member.is_married()
        status = "married" if is_married["is_married"] else "single"
        e.condition(self.screen.household_assets <= self.asset_limit[status])

        # income
        earned_income = member.calc_gross_income("yearly", ["earned"])
        unearned_income = member.calc_gross_income("yearly", ["unearned"])

        if status == "married":
            spouse = is_married["married_to"]
            earned_income += spouse.calc_gross_income("yearly", ["earned"])
            unearned_income += spouse.calc_gross_income("yearly", ["unearned"])

        # === NC-specific income disregard rules ===
        if unearned_income >= 20:
            unearned_income -= 20
        else:
            remaining = 20 - unearned_income
            unearned_income = 0
            earned_income = max(0, earned_income - remaining)

        earned_income = max(0, earned_income - 65)
        earned_income /= 2

        countable_income = unearned_income + earned_income

        household_size = self.screen.household_size
        fpl = self.program.year.as_dict()[household_size]
        min_income = fpl * self.min_income_percent
        max_income = fpl * self.max_income_percent

        e.condition(countable_income >= min_income)
        e.condition(countable_income <= max_income)
