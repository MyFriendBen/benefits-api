from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages


class MedicaidChildWithDisability(ProgramCalculator):
    program_code = "cwd_medicaid"
    # PolicyEngine-backed, and a genuine dependency rather than a proxied income test:
    # the rule is about whether Medicaid already covers this household, which is not
    # reducible to a condition on the household's own facts. PE resolves it through a
    # dozen category tests, so there is nothing to restate.
    gates_on = ("co_medicaid",)
    max_age = 18
    min_employment_age = 16
    max_income_percent = 3
    earned_deduction = 90
    income_percent = 1 - 0.33
    insurance_types = ("employer", "private", "none")
    dependencies = ["insurance", "age", "household_size", "income_type", "income_amount", "income_frequency"]
    member_amount = 200 * 12

    def household_eligible(self, e: Eligibility):
        # Does not qualify for Medicaid
        e.condition(not self.program_eligible("co_medicaid"), messages.must_not_have_benefit("Medicaid"))

        # income
        fpl = self.program.year.as_dict()
        income_limit = fpl[self.screen.household_size] * MedicaidChildWithDisability.max_income_percent
        earned = max(
            0, int(self.screen.calc_gross_income("yearly", ["earned"]) - MedicaidChildWithDisability.earned_deduction)
        )
        unearned = self.screen.calc_gross_income("yearly", ["unearned"], exclude=["nurturingFutures"])
        income = (earned + unearned) * MedicaidChildWithDisability.income_percent
        e.condition(income <= income_limit, messages.income(income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(member.age <= MedicaidChildWithDisability.max_age)

        # disability
        e.condition(member.long_term_disability or member.visually_impaired)

        # insurance
        e.condition(member.insurance.has_insurance_types(MedicaidChildWithDisability.insurance_types))

        # no income
        e.condition(
            not (
                member.calc_gross_income("yearly", ["earned"]) >= 0
                and member.age >= MedicaidChildWithDisability.min_employment_age
            )
        )
