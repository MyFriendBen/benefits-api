import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Medicaid, HeadStart
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember


class KsKanCare(Medicaid):
    """KanCare is Kansas's Medicaid program.

    Subclass of the federal PE ``medicaid`` calculator (pattern: CO/NC/MA/WA).
    Kansas has not adopted ACA adult expansion, so PE returns ineligible for
    non-disabled, non-pregnant, childless adults under 65 at any income.

    KS-specific input handling (see spec Implementation Notes 1-2):

    - ``SsiCountableResourcesDependency`` (``ssi_countable_resources``, derived from
      ``household_assets`` as ``household_assets / num_adults`` per adult) is sent, so
      the ABD $2,000/$3,000 resource test fires — consistent with every other state
      that runs Medicaid + MSP (IL/CO/MA all send it). The same ``ssi_countable_resources``
      variable also drives MSP's ``msp_asset_eligible``, and both programs share one
      PolicyEngine simulation, so KanCare and MSP must handle assets consistently: either
      both screen assets or neither. We screen for both. The per-adult sharding errs lax
      (a third adult's presence under-counts an applicant's countable resources, since PE
      sums only the applicant's marital/tax unit), which is the acceptable over-inclusive
      direction for a screener.
    - ``MeetsSsiDisabilityCriteriaDependency`` maps the screener's disability /
      long-term-disability / SSDI signals to PE's ``meets_ssi_disability_criteria``
      input (not ``is_ssi_disabled`` directly, so the SGA earnings test still
      applies). ``IsBlindDependency`` maps ``visually_impaired`` to ``is_blind``,
      which also exempts blind applicants from SGA. Without these, disabled/blind
      applicants would wrongly return ineligible (non-expansion KS has no
      adult-expansion fallback).
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
    """
    Kansas CHIP (Children's Health Insurance Program) calculator.

    Composes PolicyEngine's federal ``chip`` eligibility/value output with the
    Kansas-specific ``ks_chip_premium``. Mirrors the TxChip precedent:

    - ``chip`` (the per-child coverage value, ~``per_capita_chip``) is the member
      value. All CHIP eligibility logic (under 19, income at/below the 255% FPL
      effective cap, ~Medicaid-eligible) is already baked into PE's ``chip`` output.
    - The "uninsured children only" rule is enforced via MFB's hybrid zero-out:
      a child's CHIP value is surfaced only when their insurance is exactly
      ``none``; any other coverage type zeroes it out.

    KS-specific: additionally outputs ``ks_chip_premium`` (a TaxUnit-level PE
    variable returned as an ANNUAL figure = monthly premium x 12). It is surfaced
    for display alongside the coverage value (divide by 12 for the monthly amount)
    and is NOT netted against the coverage value.

    Dependency on KanCare Medicaid: PE gates ``is_chip_eligible_child`` on
    ``~is_medicaid_eligible``, so CHIP must compute Medicaid eligibility the same
    way KanCare does. All programs on a screen share a single PolicyEngine
    simulation (``pe_input`` merges every program's ``pe_inputs``), so CHIP reuses
    ``KsKanCare.pe_inputs`` verbatim (including ``SsiCountableResourcesDependency``)
    rather than the federal ``Medicaid.pe_inputs`` — this keeps the shared
    ``medicaid`` / ``is_medicaid_eligible`` computation identical to KanCare's.
    CHIP applies no resource test of its own; it inherits the shared asset input
    only so the Medicaid-eligibility gate it depends on is computed consistently.
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
        - MSP's asset test (``msp_asset_eligible``) reads ``ssi_countable_resources``, which MFB
          shards as ``household_assets / num_adults`` per adult. PE then sums only the applicant's
          marital unit, so in households with a third adult (e.g. an adult child) the applicant's
          countable resources are under-counted — erring lax / over-inclusive, the acceptable
          direction for a screener (known data gap)
        - Benefit value is premium savings only; QMB deductible/coinsurance coverage is not included

    Note: Includes ``*Medicaid.pe_inputs`` + IsMedicaidEligibleDependency. These serve two
    purposes: QI requires checking the individual is not eligible for other Medicaid benefits,
    AND MSP's own asset test (``msp_asset_eligible``) reads ``ssi_countable_resources``, which
    ``Medicaid.pe_inputs`` supplies. Because MSP and KanCare share one PolicyEngine simulation
    and both key off ``ssi_countable_resources``, they must treat assets consistently — KanCare
    now also sends ``SsiCountableResourcesDependency`` (see KsKanCare) so both programs screen
    assets, matching IL/CO/MA. Omitting it would break MSP's asset test; sending it from MSP
    while omitting it from KanCare would corrupt KanCare Medicaid eligibility for asset-holding
    seniors. Consistent handling avoids both failure modes.

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
        # spm_unit_cash_assets (msp_countable_income resource-related inputs; the
        # msp_asset_eligible test itself reads ssi_countable_resources from *Medicaid.pe_inputs)
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
