"""IlBccp."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies.household as household_dependency
import programs.framework.pe_dependencies.member as member_dependency


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
