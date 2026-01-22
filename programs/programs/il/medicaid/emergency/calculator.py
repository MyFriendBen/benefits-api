from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
from programs.programs.il.pe.member import IlMedicaid


class IlEmergencyMedicaid(ProgramCalculator):
    member_amount = IlMedicaid.medicaid_categories["ADULT"] * 12
    insurance_types = ["none"]
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Must qualify for Medicaid
        e.condition(medicaid_eligible(self.data))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # insurance
        e.condition(member.insurance.has_insurance_types(self.insurance_types))
