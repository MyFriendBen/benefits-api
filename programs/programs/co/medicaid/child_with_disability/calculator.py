from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class MedicaidChildWithDisability(ProgramCalculator):
    max_age = 18
    min_employment_age = 16
    max_income_percent = 3
    earned_deduction = 90
    income_percent = 1 - 0.33
    insurance_types = ("employer", "private", "none")
    dependencies = ["insurance", "age", "household_size", "income_type", "income_amount", "income_frequency"]
    member_amount = 200 * 12

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            e.condition(False)
            return
        # Does not qualify for Medicaid
        e.condition(not medicaid_eligible(self.data), messages.must_not_have_benefit("Medicaid"))

        # income
        fpl = self.program.year.as_dict()
        income_limit = fpl[self.screen.household_size] * MedicaidChildWithDisability.max_income_percent
        earned = max(
            0, int(self.screen.calc_gross_income("yearly", ["earned"]) - MedicaidChildWithDisability.earned_deduction)
        )
        unearned = self.screen.calc_gross_income("yearly", ["unearned"])
        income = (earned + unearned) * MedicaidChildWithDisability.income_percent
        e.condition(income <= income_limit, messages.income(income, income_limit))

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        if member.age is None:
            return

        # age
        e.condition(member.age <= MedicaidChildWithDisability.max_age)

        # disability
        e.condition(member.long_term_disability or member.visually_impaired)

        # insurance
        e.condition(member.insurance.has_insurance_types(MedicaidChildWithDisability.insurance_types))

        # no income
        e.condition(
            not (
                (member.calc_gross_income("yearly", ["earned"]) or 0) >= 0
                and member.age >= MedicaidChildWithDisability.min_employment_age
            )
        )
