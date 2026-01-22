from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible


class IlEmergencyMedicaid(ProgramCalculator):
    # 474 comes from IlMedicaid.medicaid_categories["ADULT"]
    member_amount = 474 * 12
    insurance_types = ["none"]
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Must qualify for Medicaid
        e.condition(medicaid_eligible(self.data))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # insurance
        e.condition(member.insurance.has_insurance_types(self.insurance_types))
