from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class MedicaidAdultWithDisability(ProgramCalculator):
    min_age = 16
    max_income_percent = 4.5
    earned_deduction = 65
    earned_percent = 0.5
    unearned_deduction = 20
    min_age = 16
    insurance_types = ("employer", "private", "none")
    dependencies = ["insurance", "age", "household_size", "income_type", "income_amount", "income_frequency"]
    member_amount = 310 * 12

    def household_eligible(self, e: Eligibility) -> None:
        # Does not qualify for Medicaid
        e.condition(not medicaid_eligible(self.data), messages.must_not_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility) -> None:
        if self.program.year is None:
            e.condition(False)
            return
        member = e.member

        # age
        if member.age is None:
            return
        e.condition(member.age >= MedicaidAdultWithDisability.min_age)

        # disability
        e.condition(member.long_term_disability or member.visually_impaired)

        # insurance
        e.condition(member.insurance.has_insurance_types(MedicaidAdultWithDisability.insurance_types))

        # income
        fpl = self.program.year.as_dict()
        income_limit = fpl[self.screen.household_size] * MedicaidAdultWithDisability.max_income_percent
        earned_deduction = MedicaidAdultWithDisability.earned_deduction
        earned_percent = MedicaidAdultWithDisability.earned_percent
        earned = max(0, int((int(member.calc_gross_income("yearly", ["earned"])) - earned_deduction) * earned_percent))
        unearned_deduction = MedicaidAdultWithDisability.unearned_deduction
        unearned = int(member.calc_gross_income("yearly", ["unearned"])) - unearned_deduction
        e.condition(earned + unearned <= income_limit)
