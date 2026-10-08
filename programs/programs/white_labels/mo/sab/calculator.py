from programs.framework.pe_base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class MoSab(PolicyEngineMembersCalculator):
    """
    Missouri Supplemental Aid to the Blind (SAB), via PolicyEngine's ``mo_ssp``.

    Eligibility and value are PolicyEngine's. ``mo_ssp`` is monthly and Missouri's figures turn
    over on July 1, so it is read at one pinned month and annualized here rather than read at
    the program year, which would sum twelve months across the change.
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
        # Unearned income. SSI is not one of PolicyEngine's SAB income sources.
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
    # Missouri's SAB figures turn over on July 1, so read a month from July on, not January.
    pe_period_month = "07"

    def member_value(self, member: HouseholdMember):
        # PE returns 0 for anyone it does not find eligible, so member eligibility falls out
        # of its own value. The x12 is ours: mo_ssp is monthly.
        return self.get_member_dependency_value(dependency.member.MoSsp, member.id) * 12
