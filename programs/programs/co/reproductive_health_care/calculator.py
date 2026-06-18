from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class ReproductiveHealthCare(ProgramCalculator):
    amount = 268
    dependencies = ["insurance"]

    def household_eligible(self, e: Eligibility) -> None:
        # Medicade eligibility
        e.condition(medicaid_eligible(self.data), messages.must_have_benefit("Medicaid"))

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # No health insurance
        has_no_hi = member.insurance.has_insurance_types(("none",))
        e.condition(has_no_hi)
