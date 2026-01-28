import programs.programs.federal.pe.member as federal_member
import programs.programs.federal.pe.tax as tax
import programs.programs.policyengine.calculators.dependencies as pe_dependency
import programs.programs.policyengine.calculators.dependencies.household as household_dependency
import programs.programs.policyengine.calculators.dependencies.member as member_dependency
import programs.programs.policyengine.calculators.dependencies.spm as spm_dependency
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator


class IlMedicaid(federal_member.Medicaid):
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
        *federal_member.Medicaid.pe_inputs,
        household_dependency.IlStateCodeDependency,
    ]


class IlWic(federal_member.Wic):
    wic_categories = {
        "NONE": 0,
        "INFANT": 130,
        "CHILD": 79,
        "PREGNANT": 104,
        "POSTPARTUM": 88,
        "BREASTFEEDING": 121,
    }
    pe_inputs = [
        *federal_member.Wic.pe_inputs,
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
    """
    Illinois Aid to the Aged, Blind, or Disabled (AABD)

    AABD provides monthly cash assistance to eligible Illinois residents who are
    aged (65+), blind, or disabled and have limited income and assets.

    Eligibility criteria:
    - SSI-eligible (aged 65+, blind, or disabled)
    - Meets income limits (countable income ≤ need standard)
    - Meets asset limits
    - Illinois resident
    - U.S. citizen or qualified immigrant

    Value: Monthly cash benefit = need standard - countable income.
    Need standard includes personal allowance, shelter allowance, and utility allowance
    based on household circumstances and IL AABD area (1-8).
    """

    pe_name = "il_aabd_person"
    pe_inputs = [
        # NOTE: Not including utility expenses (electricity, gas, water, etc.)
        # so utility allowance portion of need standard will be $0.
        # This may slightly underestimate the benefit for households paying utilities.
        # is_ssi_eligible
        member_dependency.AgeDependency,
        member_dependency.IsBlindDependency,
        member_dependency.IsDisabledDependency,
        member_dependency.SsiEarnedIncomeDependency,
        member_dependency.SsiReportedDependency,
        member_dependency.SsiCountableResourcesDependency,
        # il_aabd_countable_income - unearned income types
        member_dependency.SocialSecurityIncomeDependency,
        member_dependency.SsdiReportedDependency,
        member_dependency.Ssi,
        member_dependency.WorkersCompensationDependency,
        member_dependency.UnemploymentIncomeDependency,
        member_dependency.RetirementDistributionsDependency,
        member_dependency.AlimonyIncomeDependency,
        member_dependency.InvestmentIncomeDependency,  # covers dividend_income, interest_income, and capital_gains (combined)
        #   farm_income - not collected
        #   farm_rent_income - not collected
        #   debt_relief (cancellation_of_debt) - not collected
        #   illicit_income - not collected
        member_dependency.MiscellaneousIncomeDependency,
        # il_aabd_countable_income - earned income types
        member_dependency.EmploymentIncomeDependency,
        member_dependency.SelfEmploymentIncomeDependency,
        member_dependency.RentalIncomeDependency,
        # il_aabd_shelter_allowance
        member_dependency.RentDependency,
        member_dependency.PropertyTaxExpenseDependency,
        spm_dependency.MortgageDependency,
        spm_dependency.HoaFeesExpenseDependency,
        spm_dependency.HomeownersInsuranceExpenseDependency,
        # il_aabd_countable_assets
        spm_dependency.CashAssetsDependency,
        #   il_aabd_countable_vehicle_value - not collected
        household_dependency.IlCountyDependency,
        household_dependency.IlStateCodeDependency,
    ]
    pe_outputs = [member_dependency.IlAabd]


class IlHbwd(PolicyEngineMembersCalculator):
    """
    Illinois Health Benefits for Workers with Disabilities (HBWD).

    HBWD is a Medicaid buy-in program for working individuals with disabilities.

    PolicyEngine calculates eligibility based on:
    - Age (16-64 years via monthly_age)
    - Disability (is_disabled OR social_security_disability > 0)
    - Employment (il_hbwd_gross_earned_income > 0 as FICA proxy)
    - Income (il_hbwd_countable_income vs spm_unit_fpg threshold)
    - Assets (spm_unit_cash_assets < $25,000; vehicle value not sent since we don't have)
    - Immigration (immigration_status = citizen or qualifying noncitizen)

    Returns:
        - il_hbwd_eligible (boolean eligibility flag)
        - il_hbwd_premium (negative premium = cost to the individual, surfaced but
          not used as the program's member_value)
    """

    pe_name = "il_hbwd_person"
    pe_inputs = [
        # age eligible
        member_dependency.AgeDependency,
        # disability eligible
        member_dependency.IsDisabledDependency,
        member_dependency.SsdiReportedDependency,
        # income eligible - unearned income types
        member_dependency.SocialSecurityIncomeDependency,
        member_dependency.WorkersCompensationDependency,
        member_dependency.UnemploymentIncomeDependency,
        member_dependency.RetirementDistributionsDependency,
        member_dependency.AlimonyIncomeDependency,
        member_dependency.InvestmentIncomeDependency,  # covers dividend_income, interest_income, and capital_gains (combined)
        #   farm_income - not collected
        #   farm_rent_income - not collected
        #   debt_relief (cancellation_of_debt) - not collected
        #   illicit_income - not collected
        member_dependency.MiscellaneousIncomeDependency,
        # employment/income eligible - earned income types
        member_dependency.EmploymentIncomeDependency,
        member_dependency.SelfEmploymentIncomeDependency,
        member_dependency.IsBlindDependency,
        # asset eligibility
        #   il_aabd_countable_vehicle_value - not collected
        spm_dependency.CashAssetsDependency,
        # state requirement
        household_dependency.IlStateCodeDependency,
    ]
    pe_outputs = [member_dependency.IlHbwdEligible, member_dependency.IlHbwdPremium]

    def member_value(self, member) -> int:
        """
        Do not use IlHbwdPremium - it returns a negative premium which represents
        the cost to the individual, not the benefit value.
        """
        is_eligible = self.get_member_dependency_value(member_dependency.IlHbwdEligible, member.id)
        if is_eligible:
            # >0 member_value indicates eligible
            return 1

        return 0


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


class IlMsp(PolicyEngineMembersCalculator):
    """
    Illinois Medicare Savings Program (MSP)

    Helps pay Medicare premiums, deductibles, and coinsurance for low-income
    Medicare-eligible individuals.

    Eligibility:
        - Medicare eligible (age 65+ or SSDI for 24+ months)
        - Meets income limits (SSI methodology)
        - Meets asset limits ($9,660 individual / $14,470 couple for 2025)
        - Illinois resident

    Categories (determined by PolicyEngine):
        - QMB (≤100% FPL): Part A/B premiums, deductibles, coinsurance
        - SLMB (100-120% FPL): Part B premium only
        - QI (120-135% FPL, no other Medicaid): Part B premium only

    Limitations:
        - SSDI pathway partially supported: we don't collect months on SSDI, but
          we override Medicare eligibility for users who have Medicare selected
        - Assumes 40 quarters of Medicare-covered employment (Part A is free);
          ~99% of beneficiaries meet this threshold (per CMS)
        - Benefit value is premium savings only; QMB deductible/coinsurance
          coverage (~$1,933/year) is not included in the Policy Engine calculation

    Note: Includes IlMedicaid.pe_inputs because QI requires checking that the
    individual is not eligible for other Medicaid benefits.

    References:
        - IL DHS MSP: https://www.dhs.state.il.us/?item=33698
        - Medicare.gov MSP: https://www.medicare.gov/basics/costs/help/medicare-savings-programs
        - 2025 Medicare costs: https://www.cms.gov/newsroom/fact-sheets/2025-medicare-parts-b-premiums-and-deductibles
    """

    pe_name = "msp"
    pe_inputs = [
        # is_medicare_eligible - override PE's calculation when user has Medicare selected
        member_dependency.IsMedicareEligibleDependency,
        member_dependency.AgeDependency,
        member_dependency.SsdiReportedDependency,
        # months_receiving_social_security_disability - not collected (see limitation #1)
        # msp_countable_income (uses SSI methodology)
        member_dependency.SsiEarnedIncomeDependency,
        member_dependency.SsiUnearnedIncomeDependency,
        # msp_asset_eligible
        spm_dependency.CashAssetsDependency,
        # state
        household_dependency.IlStateCodeDependency,
        # msp_standard_part_a_premium (for benefit value calculation)
        member_dependency.MedicareQuartersOfCoverageDependency,
        # Medicaid dependencies (for is_medicaid_eligible check in MSP)
        *IlMedicaid.pe_inputs,
    ]
    pe_outputs = [
        member_dependency.MspEligible,
        member_dependency.MspCategory,
        member_dependency.Msp,
    ]

    def member_value(self, member):
        is_eligible = self.get_member_dependency_value(member_dependency.MspEligible, member.id)
        if is_eligible:
            # msp returns monthly benefit value in USD
            monthly_benefit = self.get_member_variable(member.id)

            # Convert monthly to yearly
            return int(monthly_benefit * 12)
        return 0
