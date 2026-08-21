"""KS TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class KsTanf(Tanf):
    """
    Kansas Temporary Assistance for Needy Families (TANF) — the "Successful
    Families" program. Uses PolicyEngine's KS-specific `ks_tanf` calculator
    (defined_for ``ks_tanf_eligible``) for eligibility and benefit amounts.

    Inherits from the federal TANF calculator (which supplies the demographic
    inputs — age and student status used by ``is_person_demographic_tanf_eligible``)
    and adds:

    - ``KsStateCodeDependency`` so PE resolves the KS state-specific formula.
    - ``KsCountyDependency`` so the household's county reaches PE's ``ks_tanf_county_group``
      (KEESM T-2). Without it PE falls back to Group I (Rural) statewide, shorting every
      non-rural county by the tier premium.
    - ``*irs_gross_income`` so person-level employment/self-employment and unearned
      income flow into ``tanf_gross_earned_income`` / ``tanf_gross_unearned_income``.
      PE then computes ``ks_tanf_earned_income_after_deductions`` at the person level
      ($90 work expense + 60% disregard per K.A.R. 30-4-111 / KEESM 7211). Passing a
      pre-aggregated countable figure would bypass these per-person deductions.
    - ``Ssi`` so reported SSI reaches PE. KEESM 2210 excludes SSI recipients from the
      assistance unit (``ks_tanf_is_assistance_unit_member``); without this the unit size
      is inflated and, when every member is on SSI, an ineligible household is shown as
      eligible.
    - ``PregnancyDependency`` so a pregnant adult with no child still satisfies the
      demographic test (``is_person_demographic_tanf_eligible`` is age-OR-pregnant).
    - ``CashAssetsExcludingSsiHouseholdsDependency`` so the $3,000 resource test
      (``ks_tanf_resources_eligible``, KEESM 5110) reads the household's reported assets,
      except where an SSI recipient's resources are excluded and the single reported total
      cannot be split — then no countable figure is reported.
    - ``ChildCareDependency`` / ``PreSubsidyChildcareExpensesDependency`` so childcare and
      dependent-care expenses reach PE's care deduction (K.A.R. 30-4-111(b) / KEESM 7224);
      without them the deduction never applies and the benefit is understated.
    """

    program_code = "ks_tanf"

    pe_name = "ks_tanf"
    pe_inputs = [
        # Includes receipt_contract, which ks_tanf_is_assistance_unit_member needs: it
        # excludes SSI recipients from the unit, and that should follow reported receipt
        # rather than PE's simulated SSI.
        *Tanf.pe_inputs,
        dependency.household.KsStateCodeDependency,
        dependency.household.KsCountyDependency,
        dependency.member.PregnancyDependency,
        dependency.spm.CashAssetsExcludingSsiHouseholdsDependency,
        dependency.spm.ChildCareDependency,
        dependency.spm.PreSubsidyChildcareExpensesDependency,
    ]

    pe_outputs = [dependency.spm.KsTanf]
