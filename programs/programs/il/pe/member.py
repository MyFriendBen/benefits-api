import programs.programs.federal.pe.member as member
import programs.programs.federal.pe.tax as tax
import programs.programs.policyengine.calculators.dependencies as pe_dependency
import programs.programs.policyengine.calculators.dependencies.household as household_dependency
import programs.programs.policyengine.calculators.dependencies.member as member_dependency
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator


class IlMedicaid(member.Medicaid):
    """Base Illinois Medicaid eligibility through PolicyEngine"""

    medicaid_categories = {
        "NONE": 0,
        "ADULT": 474,
        "INFANT": 0,
        "YOUNG_CHILD": 0,
        "OLDER_CHILD": 0,
        "PREGNANT": 474,
        "YOUNG_ADULT": 0,
        "PARENT": 474,
        "SSI_RECIPIENT": 474,
        "AGED": 474,
        "DISABLED": 474,
    }
    pe_inputs = [
        *member.Medicaid.pe_inputs,
        household_dependency.IlStateCodeDependency,
    ]


class IlWic(member.Wic):
    wic_categories = {
        "NONE": 0,
        "INFANT": 130,
        "CHILD": 79,
        "PREGNANT": 104,
        "POSTPARTUM": 88,
        "BREASTFEEDING": 121,
    }
    pe_inputs = [
        *member.Wic.pe_inputs,
        household_dependency.IlStateCodeDependency,
    ]


class IlAca(tax.Aca):
    pe_name = "aca_ptc"
    pe_inputs = [
        *tax.Aca.pe_inputs,
        household_dependency.IlStateCodeDependency,
        household_dependency.IlCountyDependency,
    ]


class IlAabd(PolicyEngineMembersCalculator):
    pe_name = "il_aabd_person"
    pe_inputs = [
        member_dependency.AgeDependency,
        member_dependency.IsDisabledDependency,
        member_dependency.IsBlindDependency,
        member_dependency.IlAabdGrossEarnedIncomeDependency,
        member_dependency.IlAabdGrossUnearnedIncomeDependency,
        household_dependency.IlStateCodeDependency,
    ]
    pe_outputs = [member_dependency.IlAabd]


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

    pe_name = "il_bcc_eligible"
    pe_category = "people"

    pe_inputs = [
        member_dependency.IlBccFemaleDependency,
        member_dependency.AgeDependency,
        member_dependency.IlBccInsuranceEligibleDependency,
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


class IlFamilyPlanningProgram(PolicyEngineMembersCalculator):
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
    ]
    pe_outputs = [member_dependency.IlFppEligible]

    def member_value(self, member):
        is_eligible = self.get_member_variable(member.id)
        has_disqualifying_insurance = member.has_insurance_types(("medicaid", "family_planning"), strict=False)

        if has_disqualifying_insurance or not is_eligible:
            return 0

        # Return 1 if eligible. We display "Varies" for the estimated value in the UI
        return 1


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
