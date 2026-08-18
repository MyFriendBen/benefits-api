from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
from programs.framework.helpers import medicaid_eligible
import programs.framework.eligibility_messages as messages


class ReproductiveHealthCare(ProgramCalculator):
    name_abbreviated = "rhc"
    amount = 268
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Medicade eligibility
        e.condition(medicaid_eligible(self.data), messages.must_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # No health insurance
        has_no_hi = member.insurance.has_insurance_types(("none",))
        e.condition(has_no_hi)
