from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages


class MedicaidAdultWithDisability(ProgramCalculator):
    program_code = "awd_medicaid"
    # PolicyEngine-backed, and a genuine dependency rather than a proxied income test:
    # the rule is about whether Medicaid already covers this household, which is not
    # reducible to a condition on the household's own facts. PE resolves it through a
    # dozen category tests, so there is nothing to restate.
    gates_on = ("co_medicaid",)
    min_age = 16
    max_income_percent = 4.5
    earned_deduction = 65
    earned_percent = 0.5
    unearned_deduction = 20
    min_age = 16
    insurance_types = ("employer", "private", "none")
    dependencies = ["insurance", "age", "household_size", "income_type", "income_amount", "income_frequency"]
    member_amount = 310 * 12

    def household_eligible(self, e: Eligibility):
        # Does not qualify for Medicaid
        e.condition(not self.program_eligible("co_medicaid"), messages.must_not_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
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
        unearned = (
            int(member.calc_gross_income("yearly", ["unearned"], exclude=["nurturingFutures"])) - unearned_deduction
        )
        e.condition(earned + unearned <= income_limit)
