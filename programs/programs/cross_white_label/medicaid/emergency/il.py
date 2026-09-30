from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility


class IlEmergencyMedicaid(ProgramCalculator):
    program_code = "il_emergency_medicaid"
    # PolicyEngine-backed, and a genuine dependency rather than a proxied income test:
    # the rule is about whether Medicaid already covers this household, which is not
    # reducible to a condition on the household's own facts. PE resolves it through a
    # dozen category tests, so there is nothing to restate.
    gates_on = ("il_medicaid",)
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
