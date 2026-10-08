from programs.framework.pe_base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class MoSab(PolicyEngineMembersCalculator):
    """
    Missouri Supplemental Aid to the Blind (SAB), via PolicyEngine's ``mo_ssp``.

    Eligibility and value are PolicyEngine's; see spec.md. Nothing here re-derives Missouri's
    $1,073 Consolidated Standard, its earned-income exemptions, the resource limits or the
    $949 grant less reported SSI. The notes below cover only the wiring.

    ``mo_ssp`` is a monthly variable and Missouri's figures turn over on July 1, so it is read
    at one pinned month and annualized here. Reading it at the program year returns the twelve
    months summed, which comes to $192/year low for a claimant with no SSI. See
    ``PolicyEngineCalulator.period_for``.

    Inputs that are load-bearing rather than boilerplate (each one fails silently if omitted):

    - ``MoSspLivingArrangementSabDependency`` — the arrangement defaults to ``NONE``, which pays
      $0 to everyone.
    - ``IsBlindDependency`` — ``is_blind`` defaults to False, so unsent it pays $0 to everyone.
    - ``AgeDependency`` — ``age`` defaults to 40, which clears the age-18 floor, so unsent a
      17-year-old is returned eligible.
    - ``SsiCountableResourcesDependency`` — unsent, the resource test never bites.
    - ``MoSabEarnedIncomeDependency`` — Missouri counts boarder income as earned; unsent, it
      never reaches the formula.
    - ``receipt_contract`` — the grant is $949 less the SSI the claimant *receives*, not an SSI
      entitlement computed for them. The contract makes PolicyEngine's ``ssi`` read 0 for a
      member who reports none, so they are paid the full $949.

    Reported Temporary Assistance deliberately does not gate: it is an election between two
    programs, not a bar (spec.md criterion 11).
    """

    program_code = "mo_sab"

    pe_name = "mo_ssp"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsBlindDependency,
        dependency.member.MoSspLivingArrangementSabDependency,
        dependency.member.SsiCountableResourcesDependency,
        # Earned income: Missouri's boarder rule replaces the shared wages-only mapping.
        dependency.member.MoSabEarnedIncomeDependency,
        dependency.member.SelfEmploymentIncomeDependency,
        # Unearned income. SSI is absent from PolicyEngine's SAB source list, so reported SSI
        # is not counted against the $1,073 standard (criterion 8).
        dependency.member.RentalIncomeDependency,
        dependency.member.PensionIncomeDependency,
        dependency.member.SocialSecurityIncomeDependency,
        dependency.member.UnemploymentIncomeDependency,
        dependency.member.RetirementDistributionsDependency,
        *dependency.receipt_contract,
        dependency.household.MoStateCodeDependency,
        dependency.household.MoCountyDependency,
        dependency.household.ZipCodeDependency,
    ]
    pe_outputs = [dependency.member.MoSsp]
    pe_monthly_outputs = [dependency.member.MoSsp]
    # Missouri's SAB figures turn over on July 1 (the grant maximum and the resource limits),
    # so any month from July on reads the schedule the 2026 expected values are stated against.
    # January would read the prior one.
    pe_period_month = "07"

    def member_value(self, member: HouseholdMember):
        # PE returns 0 for anyone it does not find eligible, so member eligibility falls out
        # of its own value. The x12 is ours: mo_ssp is monthly.
        return self.get_member_dependency_value(dependency.member.MoSsp, member.id) * 12
