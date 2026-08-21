from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages


class ReproductiveHealthCare(ProgramCalculator):
    program_code = "rhc"
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
