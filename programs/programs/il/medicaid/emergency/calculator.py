from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class IlEmergencyMedicaid(ProgramCalculator):
    # Monthly value from IL Medicaid categories (ADULT: 474), annualized
    member_amount = 474 * 12
    insurance_types = ["none"]
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Does qualify for Medicaid
        e.condition(medicaid_eligible(self.data), messages.must_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # insurance
        e.condition(member.insurance.has_insurance_types(IlEmergencyMedicaid.insurance_types))
