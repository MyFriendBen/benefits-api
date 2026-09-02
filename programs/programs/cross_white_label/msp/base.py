"""Medicare Savings Program."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class Msp(PolicyEngineMembersCalculator, abstract=True):
    """
    Federal Medicare Savings Program (QMB/SLMB/QI). Eligibility, category, and value
    are computed by PolicyEngine's ``msp`` variable; MSP rules are federal, so state
    subclasses only add their state-code dependency and the state's Medicaid inputs.

    The Medicaid inputs are load-bearing for MSP in two ways:
        - QI eligibility requires the applicant NOT be eligible for full Medicaid, so ``msp``
          reads ``is_medicaid_eligible`` — which is only computed when the Medicaid inputs
          (age, income, disability, pregnancy) are present in the shared simulation.
        - MSP's asset test (``msp_asset_eligible``) reads ``ssi_countable_resources``, which is
          supplied by ``SsiCountableResourcesDependency`` from the Medicaid input set.
    Without the Medicaid inputs, QI would never exclude Medicaid-eligible applicants and the
    asset test would see $0 resources.

    Categories: QMB (≤100% FPL, Part A/B premiums + deductibles + coinsurance),
    SLMB (100-120% FPL, Part B premium), QI (120-135% FPL and not Medicaid-eligible,
    Part B premium).

    Limitations:
        - SSDI pathway partial: months_receiving_social_security_disability isn't collected,
          but IsMedicareEligibleDependency short-circuits when the user reports Medicare.
        - Assumes 40 quarters of covered employment (free Part A); ~99% of beneficiaries qualify.
        - Benefit value is premium savings only (no QMB deductible/coinsurance).
    """

    pe_name = "msp"
    pe_inputs = [
        dependency.member.IsMedicareEligibleDependency,
        dependency.member.AgeDependency,
        dependency.member.SsdiReportedDependency,
        # MSP's income test (msp_countable_income) uses SSI income methodology,
        # so send SSI earned/unearned income rather than plain gross income.
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        dependency.spm.CashAssetsDependency,
        dependency.member.MedicareQuartersOfCoverageDependency,
        dependency.member.IsMedicaidEligibleDependency,
        # msp_countable_income uses SSI methodology and msp_category has an SSI pathway.
        *dependency.receipt_contract,
    ]
    pe_outputs = [
        dependency.member.MspEligible,
        dependency.member.MspCategory,
        dependency.member.Msp,
    ]
