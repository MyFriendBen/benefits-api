"""Child Care and Development Fund (CCDF) — shared base."""

from screener.models import HouseholdMember

from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework import pe_dependencies as dependency


class Ccdf(PolicyEngineMembersCalculator, abstract=True):
    pe_name = "is_ccdf_eligible"
    pe_inputs = [
        dependency.spm.AssetsDependency,
        dependency.member.CcdfReasonCareEligibleDependency,
        dependency.member.EmploymentIncomeDependency,
        dependency.member.SelfEmploymentIncomeDependency,
        dependency.member.PensionIncomeDependency,
        dependency.member.InvestmentIncomeDependency,
        dependency.member.RentalIncomeDependency,
        dependency.member.MiscellaneousIncomeDependency,
    ]
    pe_outputs = [dependency.member.Ccdf]

    def child_care_cost(self, member: HouseholdMember) -> int:
        raise NotImplemented("Please define the 'child_care_cost' method")

    def member_value(self, member: HouseholdMember):
        if not self.get_member_variable(member.id):
            return 0

        return self.child_care_cost(member)
