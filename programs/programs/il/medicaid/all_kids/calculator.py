from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
from programs.framework.helpers import medicaid_eligible
import programs.framework.eligibility_messages as messages
from programs.framework.mixins import IlMedicaidFplIncomeCheckMixin


class AllKids(ProgramCalculator, IlMedicaidFplIncomeCheckMixin):
    member_amount = 284 * 12  # $284/month
    max_age = 18  # Under 19
    dependencies = ["age", "household_size", "pregnant", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility):
        # Check income against 318% FPL
        self.check_fpl_income(e, 3.18)

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Must be under 19
        e.condition(member.age <= self.max_age)

        # Must not have Medicaid
        e.condition(not member.has_insurance("medicaid"))

        # Must not already have All Kids (chp)
        e.condition(not member.has_insurance("chp"))
