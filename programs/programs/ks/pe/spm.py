import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Tanf


class KsTanf(Tanf):
    """
    Kansas Temporary Assistance for Needy Families (TANF) — the "Successful
    Families" program. Uses PolicyEngine's KS-specific `ks_tanf` calculator
    (defined_for ``ks_tanf_eligible``) for eligibility and benefit amounts.

    Inherits from the federal TANF calculator (which supplies the demographic
    inputs — age and student status used by ``is_person_demographic_tanf_eligible``)
    and adds:

    - ``KsStateCodeDependency`` so PE resolves the KS state-specific formula.
    - ``*irs_gross_income`` so person-level employment/self-employment and unearned
      income flow into ``tanf_gross_earned_income`` / ``tanf_gross_unearned_income``.
      PE then computes ``ks_tanf_earned_income_after_deductions`` at the person level
      ($90 work expense + 60% disregard per K.A.R. 30-4-111 / KEESM 7211). Passing a
      pre-aggregated countable figure would bypass these per-person deductions.
    - ``PregnancyDependency`` so a pregnant adult with no child still satisfies the
      demographic test (``is_person_demographic_tanf_eligible`` is age-OR-pregnant).
    - ``CashAssetsDependency`` so the $3,000 resource test (``ks_tanf_resources_eligible``,
      KEESM 5110) reads the household's reported assets instead of defaulting to 0.

    Note on benefit amount: PE's ``ks_tanf_maximum_benefit`` returns the Group IV
    non-shared-living payment standard (basic + $135 shelter) as the cross-state
    research convention; it does not vary the shelter allowance by Kansas county
    group or model shared-living reductions.
    """

    pe_name = "ks_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.KsStateCodeDependency,
        dependency.member.PregnancyDependency,
        dependency.spm.CashAssetsDependency,
        *dependency.irs_gross_income,
    ]

    pe_outputs = [dependency.spm.KsTanf]
