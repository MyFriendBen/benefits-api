import programs.programs.federal.pe.member as federal_member
import programs.programs.federal.pe.tax as tax
import programs.framework.pe_dependencies as pe_dependency
import programs.framework.pe_dependencies.household as household_dependency
import programs.framework.pe_dependencies.member as member_dependency
import programs.framework.pe_dependencies.spm as spm_dependency
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.programs.cross_white_label.medicaid.il import IlMedicaid
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.ssi.base import Ssi


class IlBccp(PolicyEngineMembersCalculator):
    """
    Illinois Breast and Cervical Cancer Program (IBCCP)

    This program provides health insurance coverage for breast and cervical cancer
    screening services for eligible Illinois residents. Note: This program also
    covers cancer treatment for individuals diagnosed with breast or cervical cancer
    or certain precancerous conditions. For treatment eligibility, additional criteria
    apply including medical diagnosis and pathology documentation.

    Eligibility criteria for screening:
    - Female
    - Under 65 years old
    - Not eligible for Medicaid, All Kids, or other HFS insurance
    """

    program_code = "il_ibccp"

    pe_name = "il_bcc_eligible"
    pe_category = "people"

    pe_inputs = [
        member_dependency.IlBccFemaleDependency,
        member_dependency.AgeDependency,
        member_dependency.ReceivesMedicaidDependency,
        member_dependency.HasBccQualifyingCoverageDependency,
        household_dependency.IlStateCodeDependency,
    ]

    pe_outputs = [
        member_dependency.IlBccEligible,
    ]

    def member_value(self, member):
        """
        Calculate benefit value based on PolicyEngine eligibility.

        2025 Value Estimate - out-of-pocket costs without coverage:
            Screening mammogram: $100–$250
            Diagnostic mammogram: $250–$450
            Breast biopsy: $700–$2,000+
            Pap + HPV cotest: $100–$200

        Return average for screening services only if eligible, 0 otherwise.
        """
        # Get PolicyEngine's eligibility determination
        is_eligible = super().member_value(member)

        # If PolicyEngine says eligible (returns True/1), return estimated value
        # Otherwise return 0
        if is_eligible:
            return 400

        return 0


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
