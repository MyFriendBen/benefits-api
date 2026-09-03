from datetime import date
from typing import Optional

from screener.models import HouseholdMember
from programs.framework.base import MemberEligibility, ProgramCalculator


class MaBabySteps(ProgramCalculator):
    """
    BabySteps Savings Plan (MA)

    Massachusetts seeds a one-time $50 deposit into a MEFA U.Fund 529 account for each
    qualifying child. Eligibility is evaluated per child, so a household with multiple
    qualifying children is worth $50 per child.

    Eligibility rules, sourcing, and the handling of unavailable screener data are
    documented in spec.md.
    """

    program_code = "ma_bsp"

    member_amount = 50
    program_start = date(2020, 1, 1)
    enrollment_window_months = 12
    beneficiary_relationships = ["child", "fosterChild", "grandChild", "sibling", "other"]
    dependencies = ["relationship", "birth_year"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        e.condition(self.is_beneficiary_candidate(member.relationship))
        e.condition(self.birth_pathway_eligible(member))

    def is_beneficiary_candidate(self, relationship: Optional[str]) -> bool:
        """Whether a `relationship` value describes a possible BabySteps beneficiary."""
        return relationship in self.beneficiary_relationships

    def birth_pathway_eligible(self, member: HouseholdMember) -> bool:
        """
        Whether the member is inside the enrollment window: born on or after `program_start`
        and no more than `enrollment_window_months` ago.

        The screener collects birth month and year but not day, so the whole first-birthday
        month counts as inside the window.
        """
        birth_year_month = member.birth_year_month
        if birth_year_month is None:
            return False

        if birth_year_month < self.program_start:
            return False

        reference_date = self.screen.get_reference_date()
        months_since_birth = (reference_date.year - birth_year_month.year) * 12 + (
            reference_date.month - birth_year_month.month
        )

        return 0 <= months_since_birth <= self.enrollment_window_months
