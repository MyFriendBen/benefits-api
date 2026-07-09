import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Medicaid, HeadStart
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember


class KsKanCare(Medicaid):
    """KanCare is Kansas's Medicaid program (subclass of the federal ``medicaid`` calculator).

    Kansas has not adopted ACA adult expansion, so PE returns ineligible for
    non-disabled, non-pregnant, childless adults under 65 at any income.

    KS-specific inputs beyond the federal Medicaid set:

    - ``SsiCountableResourcesDependency`` screens the ABD $2,000/$3,000 resource limit.
    - ``MeetsSsiDisabilityCriteriaDependency`` / ``IsBlindDependency`` map the screener's
      disability, long-term-disability, SSDI, and visual-impairment signals to PE's
      SSI-criterion inputs (leaving the SGA earnings test intact). Without them,
      disabled/blind applicants would wrongly return ineligible.
    """

    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.MeetsSsiDisabilityCriteriaDependency,
        dependency.member.IsBlindDependency,
        dependency.member.SsiCountableResourcesDependency,
        *dependency.irs_gross_income,
        dependency.household.KsStateCodeDependency,
    ]

    # KHI / Kansas Action for Children FY2023 KS Medicaid & CHIP per-enrollee
    # spending by group, monthly (annual figure returned = value * 12):
    #   MAGI groups  -> $3,644/yr  -> $304/mo
    #   aged (65+)   -> $20,511/yr -> $1,709/mo
    #   disabled     -> $32,459/yr -> $2,705/mo
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 304,
        "INFANT": 304,
        "YOUNG_CHILD": 304,
        "OLDER_CHILD": 304,
        "PREGNANT": 304,
        "YOUNG_ADULT": 304,
        "PARENT": 304,
        "SSI_RECIPIENT": 2705,
        "AGED": 1709,
        "DISABLED": 2705,
    }


class KsChip(PolicyEngineMembersCalculator):
    """Kansas CHIP calculator (mirrors the TxChip precedent).

    Member value is PE's federal ``chip`` output (all CHIP eligibility logic — under 19,
    income ≤ the 255% FPL effective cap, not Medicaid-eligible — is already baked in),
    surfaced only for children whose insurance is exactly ``none``. Also outputs the
    Kansas ``ks_chip_premium`` (annual = monthly premium × 12) for display; it is not
    netted against the coverage value.

    PE gates CHIP on ``~is_medicaid_eligible``, so CHIP reuses ``KsKanCare.pe_inputs``
    to compute Medicaid eligibility the same way KanCare does. CHIP applies no resource
    test of its own.
    """

    pe_name = "chip"
    pe_inputs = [
        *KsKanCare.pe_inputs,
    ]
    pe_outputs = [
        dependency.member.Chip,
        dependency.tax.KsChipPremium,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the CHIP coverage value for this member, applying the
        uninsured-only rule.
        """
        pe_value = self.get_member_variable(member.id)

        # CHIP is only for children with no other health coverage. Any insurance
        # type other than "none" disqualifies the child.
        if member.has_insurance_types(("none",)):
            return pe_value

        return 0


class KsMsp(PolicyEngineMembersCalculator):
    """Kansas Medicare Savings Program (QMB/SLMB/QI), using PolicyEngine's federal ``msp``
    calculator as-is (no Kansas-specific variance).

    Categories, determined by PE: QMB (≤100% FPL, Part A/B premiums + deductibles +
    coinsurance), SLMB (100-120% FPL, Part B premium), QI (120-135% FPL and not
    Medicaid-eligible, Part B premium).

    Limitations inherited from the federal calculator:
        - SSDI pathway partial: months_receiving_social_security_disability isn't collected,
          but IsMedicareEligibleDependency short-circuits when the user reports Medicare.
        - Assumes 40 quarters of covered employment (free Part A); ~99% of beneficiaries qualify.
        - Assets are screened against ``household_assets / num_adults`` per adult; PE sums only
          the applicant's marital unit, so a third adult under-counts resources (lax, the
          acceptable over-inclusive direction).
        - Benefit value is premium savings only (no QMB deductible/coinsurance).

    References:
        - https://www.medicare.gov/basics/costs/help/medicare-savings-programs
        - https://www.cms.gov/newsroom/fact-sheets/2026-medicare-parts-b-premiums-deductibles
    """

    pe_name = "msp"
    pe_inputs = [
        # is_medicare_eligible: overrides PE when the user reports Medicare
        dependency.member.IsMedicareEligibleDependency,
        dependency.member.AgeDependency,
        dependency.member.SsdiReportedDependency,
        # msp_countable_income (SSI methodology)
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        dependency.spm.CashAssetsDependency,
        dependency.household.KsStateCodeDependency,
        # 40 quarters -> free Part A -> QMB value is the Part B premium
        dependency.member.MedicareQuartersOfCoverageDependency,
        # is_medicaid_eligible for the QI exclusion; overrides when the user reports Medicaid
        dependency.member.IsMedicaidEligibleDependency,
        # Medicaid inputs power is_medicaid_eligible and the msp_asset_eligible resource test
        *Medicaid.pe_inputs,
    ]
    pe_outputs = [
        dependency.member.MspEligible,
        dependency.member.MspCategory,
        dependency.member.Msp,
    ]


class KsHeadStart(HeadStart):
    """
    Kansas Head Start (ages 3-5). Thin wrapper on the federal ``HeadStart`` PE
    calculator that adds the KS state code; all eligibility and the per-child
    value are computed by PolicyEngine with no KS-specific variance. Early Head
    Start (birth to age 3, and pregnant women) is a separate program.
    """

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
