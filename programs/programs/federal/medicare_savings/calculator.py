from programs.programs.calc import MemberEligibility, ProgramCalculator


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
    dependencies = ["household_assets", "relationship", "income_frequency", "income_amount", "age"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(member.age >= self.min_age)

        # insurance
        e.condition(member.insurance.has_insurance_types(self.eligible_insurance_types))

        # assets
        is_married = member.is_married()
        status = "married" if is_married["is_married"] else "single"
        e.condition(self.screen.household_assets <= self.asset_limit[status])

        # income
        earned_income = member.calc_gross_income("yearly", ["earned"])
        unearned_income = member.calc_gross_income("yearly", ["unearned"], ["sSI"])
        ssi_income = member.calc_gross_income("yearly", ["sSI"])
        if status == "married":
            spouse = is_married["married_to"]
            earned_income += spouse.calc_gross_income("yearly", ["earned"])
            unearned_income += spouse.calc_gross_income("yearly", ["unearned"], ["sSI"])
            ssi_income += spouse.calc_gross_income("yearly", ["sSI"])

        # apply $20 general income disregard
        if unearned_income >= self.general_income_disregard:
            unearned_income -= self.general_income_disregard
        else:
            remaining_disregard = self.general_income_disregard - unearned_income
            unearned_income = 0
            earned_income -= remaining_disregard

        # apply $65 earned income disregard
        earned_income = max(0, earned_income - self.earned_income_disregard)

        # halve remaining earned income
        earned_income /= 2

        countable_income = unearned_income + earned_income + ssi_income

        household_size = self.screen.household_size
        fpl = self.program.year.as_dict()[household_size]
        max_income = fpl * self.max_income_percent

        e.condition(countable_income <= max_income)
