import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Medicaid, Ssi
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember


class KsSsi(Ssi):
    """
    Kansas Supplemental Security Income — federal SSI applied to KS residents.

    A thin wrapper around the federal ``Ssi`` PolicyEngine calculator that adds the
    KS state code so PolicyEngine can apply state-specific SSI handling. Kansas pays
    no general SSI state supplement (the KS supplement, SSPP, is tracked as its own
    program), so the output is the federal Federal Benefit Rate (FBR) minus
    PolicyEngine's countable income. The FBR is sourced from PolicyEngine's
    parameters at calculation time, so the value tracks SSA COLA updates year over
    year. 
    """

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]


class KsKanCare(Medicaid):
    """KanCare is Kansas's Medicaid program.

    Subclass of the federal PE ``medicaid`` calculator (pattern: CO/NC/MA/WA).
    Kansas has not adopted ACA adult expansion, so PE returns ineligible for
    non-disabled, non-pregnant, childless adults under 65 at any income.

    KS-specific input handling (see spec Implementation Notes 1-2):

    - The federal ``SsiCountableResourcesDependency`` (``ssi_countable_resources``,
      from ``household_assets``) is intentionally omitted so the ABD $2,000/$3,000
      asset test never fires. MFB does not screen assets for this pathway; the
      limit is surfaced in the program description instead. Income-eligible
      seniors/ABD applicants therefore stay eligible.
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
    ``KsKanCare.pe_inputs`` verbatim rather than the federal ``Medicaid.pe_inputs``.
    This keeps the shared ``medicaid`` / ``is_medicaid_eligible`` computation
    consistent and — critically — omits ``SsiCountableResourcesDependency``. If CHIP
    sent ``ssi_countable_resources``, that input would leak into the shared sim and
    re-enable the ABD asset gate that KanCare intentionally drops (Medicaid spec
    Implementation Note 2), wrongly making income-eligible seniors/ABD applicants
    ineligible for Medicaid whenever CHIP is also active. The asset input is not
    needed for CHIP either — KanCare CHIP applies no resource test.
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
