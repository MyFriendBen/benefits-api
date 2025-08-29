from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages
from programs.programs.mixins import FplIncomeCheckMixin


class AllKids(ProgramCalculator, FplIncomeCheckMixin):
    member_amount = 284 * 12  # $284/month
    max_age = 18  # Under 19
    dependencies = ["age", "household_size", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility):
        # Check income against 318% FPL
        self.check_fpl_income(e, 3.18)

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Must be under 19
        e.condition(member.age <= self.max_age)

        # Must not have Medicaid
        e.condition(not member.has_benefit("medicaid"))

        # Must not already have All Kids (chp)
        e.condition(not member.has_benefit("chp"))
