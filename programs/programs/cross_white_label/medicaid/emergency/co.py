from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages


class CoEmergencyMedicaid(ProgramCalculator):
    program_code = "emergency_medicaid"
    # PolicyEngine-backed, and a genuine dependency rather than a proxied income test:
    # the rule is about whether Medicaid already covers this household, which is not
    # reducible to a condition on the household's own facts. PE resolves it through a
    # dozen category tests, so there is nothing to restate.
    gates_on = ("co_medicaid",)
    amount = 9_540
    insurance_types = ["none"]
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Does qualify for Medicaid
        e.condition(self.program_eligible("co_medicaid"), messages.must_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # insurance
        e.condition(member.insurance.has_insurance_types(self.insurance_types))
