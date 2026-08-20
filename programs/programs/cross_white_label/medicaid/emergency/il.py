from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility


class IlEmergencyMedicaid(ProgramCalculator):
    program_code = "il_emergency_medicaid"
    # Average ER visit cost in Illinois for uninsured, moderate-to-severe visit
    # Source: https://www.talktomira.com/post/how-much-does-an-er-visit-cost
    member_amount = 2_000
    insurance_types = ["none"]
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility):
        # Must qualify for Medicaid
        e.condition(self.program_eligible("il_medicaid"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # No insurance
        e.condition(member.insurance.has_insurance_types(self.insurance_types))
