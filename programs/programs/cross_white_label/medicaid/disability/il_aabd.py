"""IlAabd."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies.household as household_dependency
import programs.framework.pe_dependencies.member as member_dependency
import programs.framework.pe_dependencies as pe_dependency
import programs.framework.pe_dependencies.spm as spm_dependency


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

    program_code = "il_aabd"

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
        member_dependency.SsiCountableResourcesDependency,
        # il_aabd_countable_income - unearned income types
        member_dependency.SocialSecurityIncomeDependency,
        member_dependency.SsdiReportedDependency,
        # AABD counts SSI as unearned income, so simulated SSI would block an applicant
        # with income they never received. Supplies member_dependency.Ssi.
        *pe_dependency.receipt_contract,
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
