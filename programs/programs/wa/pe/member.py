import programs.framework.pe_dependencies as dependency
from programs.programs.federal.pe.member import Ssi
from programs.framework.pe_base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.base import Medicaid


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


class WaSsi(Ssi):
    """
    Washington Supplemental Security Income — federal SSI applied to WA residents.

    A thin wrapper around the federal `Ssi` PolicyEngine calculator that adds the
    WA state code so PolicyEngine can apply state-specific SSI rules. Washington
    pays no general SSI state supplement (a small supplement exists for narrow
    residential-care categories that are out of scope for the screener), so the
    output is the federal Federal Benefit Rate (FBR) — published annually by the
    SSA — minus PolicyEngine's countable income. The current FBR is sourced from
    PolicyEngine's parameters at calculation time, not pinned in this file, so
    the calculator naturally tracks SSA cost-of-living adjustments year over year.

    All eligibility math (categorical entry: aged / disabled / blind, the
    $20 + $65 + 1/2 income exclusion stack, SGA cutoff, in-kind support and
    maintenance reductions, spousal and parental deeming, resource limits)
    is handled by PolicyEngine. The screener contributes only:
      - the per-member SSI input dependencies inherited from `Ssi.pe_inputs`
      - the WA state code so PE knows which state to model

    Duplicate-enrollment filtering ("not already receiving SSI") is enforced
    one layer up via `Screen.has_benefit("wa_ssi")`, which reads from the
    `CurrentBenefit` join table.

    See `programs/programs/wa/ssi/spec.md` for the full eligibility criteria,
    PolicyEngine variable mapping, and the 15 reference test scenarios.
    """

    program_code = "wa_ssi"

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
