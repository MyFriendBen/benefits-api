"""WaAppleHealthForKids."""

from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class WaAppleHealthForKids(PolicyEngineMembersCalculator):
    """
    WA Apple Health for Kids (WAC 182-505-0210, WAC 182-505-0215).

    MAGI-based health coverage for children under 19 in Washington.
    Free tier ≤215% effective FPL; premium tiers up to 317% effective FPL.
    Cover All Kids extends eligibility regardless of immigration status.

    Criterion 6 (premium-tier other-coverage check) is a screener data gap:
    cannot distinguish PEBB/SEBB employer coverage (exempt) from other employer
    coverage (disqualifying). Inclusivity assumption applies — no insurance
    gating at screening time.

    Value: $2,801/year per eligible child (KFF 2023 CHILD bucket).
    """

    program_code = "wa_apple_health_for_kids"

    pe_name = "wa_apple_health_kids_eligible"
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
    pe_outputs = [dependency.member.WaAppleHealthKidsEligible]

    ANNUAL_VALUE_PER_CHILD = 2_801

    def member_value(self, member: HouseholdMember):
        pe_eligible = self.get_member_variable(member.id)
        if not pe_eligible:
            return 0
        return self.ANNUAL_VALUE_PER_CHILD
