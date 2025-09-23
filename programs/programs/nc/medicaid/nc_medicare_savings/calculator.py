from programs.programs.calc import MemberEligibility, ProgramCalculator
from typing import ClassVar


class MedicareSavingsNC(ProgramCalculator):
    eligible_insurance_types: ClassVar[tuple[str, ...]] = (
        "none",
        "employer",
        "private",
        "medicare",
    )
    ineligible_insurance_types: ClassVar[tuple[str, ...]] = ("va", "medicaid")
    asset_limit: ClassVar[dict[str, int]] = {"single": 9_660, "married": 14_470}
    min_age: ClassVar[int] = 65
    min_income_percent: ClassVar[float] = 1.0
    max_income_percent: ClassVar[float] = 1.35
    member_amount: ClassVar[int] = 185 * 12
    earned_income_disregard: ClassVar[float] = 65
    general_income_disregard: ClassVar[int] = 20

    dependencies: ClassVar[list[str]] = [
        "household_assets",
        "relationship",
        "income_frequency",
        "income_amount",
        "age",
        "insurance",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(member.age >= self.min_age)

        # not on benefits
        e.condition(not self.screen.has_benefit("aca"))
        e.condition(not self.screen.has_benefit("medicaid"))

        # insurance
        e.condition(member.insurance.has_insurance_types(self.eligible_insurance_types))
        e.condition(not member.insurance.has_insurance_types(self.ineligible_insurance_types))

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
        if unearned_income >= self.general_income_disregard:
            unearned_income -= self.general_income_disregard
        else:
            remaining = self.general_income_disregard - unearned_income
            unearned_income = 0
            earned_income = max(0, earned_income - remaining)

        earned_income = max(0, earned_income - self.earned_income_disregard)
        earned_income /= 2

        countable_income = unearned_income + earned_income

        household_size = self.screen.household_size
        fpl = self.program.year.as_dict()[household_size]
        min_income = fpl * self.min_income_percent
        max_income = fpl * self.max_income_percent

        e.condition(countable_income >= min_income)
        e.condition(countable_income <= max_income)
