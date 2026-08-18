from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
from programs.framework.helpers import medicaid_eligible
import programs.framework.eligibility_messages as messages


class CoEmergencyMedicaid(ProgramCalculator):
    name_abbreviated = "emergency_medicaid"
    amount = 9_540
    insurance_types = ["none"]
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Does qualify for Medicaid
        e.condition(medicaid_eligible(self.data), messages.must_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # insurance
        e.condition(member.insurance.has_insurance_types(self.insurance_types))
