"""IL family planning — shared base for HFS FPP and FPPE."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies.household as household_dependency
import programs.framework.pe_dependencies.member as member_dependency
import programs.framework.pe_dependencies as pe_dependency


class IlFamilyPlanningProgram(PolicyEngineMembersCalculator, abstract=True):
    """
    Illinois Family Planning Program (FPP) eligibility calculator.

    This calculator is used for both:
    - HFS Family Planning Program (il_hfs_fpp) - requires qualified immigration status
    - Family Planning Presumptive Eligibility (il_fppe) - no immigration status required

    Both programs share the same eligibility logic through PolicyEngine's il_fpp_eligible variable.
    """

    pe_name = "il_fpp_eligible"
    pe_inputs = [
        *pe_dependency.irs_gross_income,
        member_dependency.TaxUnitHeadDependency,
        member_dependency.TaxUnitSpouseDependency,
        household_dependency.IlStateCodeDependency,
        member_dependency.PregnancyDependency,
        member_dependency.ReceivesMedicaidDependency,
    ]
    pe_outputs = [member_dependency.IlFppEligible]

    def member_value(self, member):
        is_eligible = self.get_member_variable(member.id)

        if not is_eligible:
            return 0

        # Return 1 if eligible. We display "Varies" for the estimated value in the UI
        return 1
