from programs.programs.federal.pe.member import Medicaid
from programs.programs.policyengine.calculators.base import (
    PolicyEngineMembersCalculator,
)
import programs.programs.policyengine.calculators.dependencies as dependency


class KsMsp(PolicyEngineMembersCalculator):
    """
    Kansas Medicare Savings Program (MSP) calculator using PolicyEngine.

    Helps pay Medicare premiums, deductibles, and coinsurance for low-income
    Medicare-eligible Kansas residents. Uses PolicyEngine's federal ``msp``
    calculator as-is — there is no Kansas-specific variance in eligibility or
    benefit value (federal rules apply statewide).

    Categories (determined by PolicyEngine):
        - QMB (≤100% FPL): Part A/B premiums, deductibles, coinsurance
        - SLMB (100-120% FPL): Part B premium only
        - QI (120-135% FPL, not Medicaid-eligible): Part B premium only

    Limitations (inherited from the federal calculator):
        - SSDI pathway partially supported: we don't collect months_receiving_social_security_disability,
          but IsMedicareEligibleDependency short-circuits for users who have Medicare selected
        - Assumes 40 quarters of Medicare-covered employment (Part A is free); ~99% of beneficiaries
          meet this threshold (per CMS)
        - household_assets (household-level total) is passed directly to PolicyEngine for all household
          sizes. MSP only counts the applicant's and spouse's resources, so for households with
          non-eligible members (e.g., adult children), this may be stricter than the actual rule (known data gap)
        - Benefit value is premium savings only; QMB deductible/coinsurance coverage is not included

    Note: Includes Medicaid pe_inputs + IsMedicaidEligibleDependency because QI requires checking
    that the individual is not eligible for other Medicaid benefits.

    References:
        - Medicare Savings Programs: https://www.medicare.gov/basics/costs/help/medicare-savings-programs
        - 2026 Medicare costs: https://www.cms.gov/newsroom/fact-sheets/2026-medicare-parts-b-premiums-deductibles
    """

    pe_name = "msp"
    pe_inputs = [
        # is_medicare_eligible - override PE's calculation when user has Medicare selected
        dependency.member.IsMedicareEligibleDependency,
        dependency.member.AgeDependency,
        dependency.member.SsdiReportedDependency,
        # months_receiving_social_security_disability - not collected (see limitation above)
        # msp_countable_income (uses SSI methodology)
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        # msp_asset_eligible
        dependency.spm.CashAssetsDependency,
        # state
        dependency.household.KsStateCodeDependency,
        # Sends 40 quarters → is_premium_free_part_a=True → base_part_a_premium=$0
        # QMB benefit value = Part B premium only (~99% of beneficiaries have free Part A)
        dependency.member.MedicareQuartersOfCoverageDependency,
        # is_medicaid_eligible (for QI exclusion) - override when user reports Medicaid
        dependency.member.IsMedicaidEligibleDependency,
        # Medicaid dependencies (for PolicyEngine's is_medicaid_eligible calculation)
        *Medicaid.pe_inputs,
    ]
    pe_outputs = [
        dependency.member.MspEligible,
        dependency.member.MspCategory,
        dependency.member.Msp,
    ]
