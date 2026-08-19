"""IL Medicaid Presumptive Eligibility (pregnancy)."""

import programs.programs.federal.pe.member as federal_member
import programs.framework.pe_dependencies as pe_dependency
import programs.framework.pe_dependencies.household as household_dependency
import programs.framework.pe_dependencies.member as member_dependency
from programs.framework.pe_base import PolicyEngineMembersCalculator


class IlMpe(PolicyEngineMembersCalculator):
    """
    Illinois Medicaid Presumptive Eligibility (Pregnancy)

    Eligibility criteria:
        - Illinois resident
        - Pregnant
        - Meets income requirements for Medicaid Presumptive Eligibility
        (as determined by PolicyEngine using the Medicaid income level -
        approximately 200% of the FPL)
        - Not already enrolled in Medicaid for the eligible individual
    """

    program_code = "il_mpe"

    pe_name = "il_mpe_eligible"
    pe_category = "people"

    pe_inputs = [
        member_dependency.AgeDependency,
        *pe_dependency.irs_gross_income,
        member_dependency.ExpectedChildrenPregnancyDependency,
        household_dependency.IlStateCodeDependency,
        member_dependency.PregnancyDependency,
    ]

    pe_outputs = [
        member_dependency.IlMpeEligible,
    ]

    def member_value(self, member):
        is_eligible = super().member_value(member)

        has_medicaid = member.has_insurance_types(("medicaid",), strict=False)
        if has_medicaid or not is_eligible:
            return 0

        return 1
