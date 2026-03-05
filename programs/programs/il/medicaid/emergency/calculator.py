from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible


class IlEmergencyMedicaid(ProgramCalculator):
    # Average ER visit cost in Illinois for uninsured, moderate-to-severe visit
    # Source: https://www.talktomira.com/post/how-much-does-an-er-visit-cost
    member_amount = 2_000
    insurance_types = ["none"]
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Must qualify for Medicaid
        e.condition(medicaid_eligible(self.data))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # No insurance
        e.condition(member.insurance.has_insurance_types(self.insurance_types))
