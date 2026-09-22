from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages


class ReproductiveHealthCare(ProgramCalculator):
    program_code = "rhc"
    # PolicyEngine-backed, and a genuine dependency rather than a proxied income test:
    # the rule is about whether Medicaid already covers this household, which is not
    # reducible to a condition on the household's own facts. PE resolves it through a
    # dozen category tests, so there is nothing to restate.
    gates_on = ("co_medicaid",)
    amount = 268
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Medicade eligibility
        e.condition(self.program_eligible("co_medicaid"), messages.must_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # No health insurance
        has_no_hi = member.insurance.has_insurance_types(("none",))
        e.condition(has_no_hi)
