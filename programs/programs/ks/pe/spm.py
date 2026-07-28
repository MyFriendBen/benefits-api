import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap, SchoolLunch, Lifeline, Tanf


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
    - ``CashAssetsDependency`` so the $3,000 resource test (``ks_tanf_resources_eligible``,
      KEESM 5110) reads the household's reported assets instead of defaulting to 0.
    - ``ChildCareDependency`` / ``PreSubsidyChildcareExpensesDependency`` so childcare and
      dependent-care expenses reach PE's care deduction (K.A.R. 30-4-111(b) / KEESM 7224);
      without them the deduction never applies and the benefit is understated.
    """

    pe_name = "ks_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.KsStateCodeDependency,
        dependency.household.KsCountyDependency,
        dependency.member.PregnancyDependency,
        dependency.member.Ssi,
        dependency.spm.CashAssetsDependency,
        dependency.spm.ChildCareDependency,
        dependency.spm.PreSubsidyChildcareExpensesDependency,
        *dependency.irs_gross_income,
    ]

    pe_outputs = [dependency.spm.KsTanf]


class KsSnap(Snap):
    """
    Kansas Food Assistance (SNAP) calculator.

    Uses PolicyEngine's federal SNAP calculator. SNAP is a federal program with
    no Kansas-specific calculator variance; state elections (BBCE, vehicle
    exemptions, utility regions) are keyed off the state code in PolicyEngine's
    SNAP parameters, so passing the KS state code is all that is required.
    """

    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]


class KsNslp(SchoolLunch):
    """
    Kansas National School Lunch Program (NSLP) calculator.

    Uses PolicyEngine's federal SchoolLunch calculator (pe_name
    ``school_meal_daily_subsidy``) as-is — NSLP is a federal program with two
    federal income tiers (free at <=130% FPG, reduced-price at <=185% FPG) and
    no Kansas-specific variance. Mirrors the tx_nslp / il_nslp precedents:
    inherit the federal eligibility/value logic and add the KS state code so
    PolicyEngine resolves any state-keyed parameters correctly.
    """

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]


class KsLifeline(Lifeline):
    """
    Kansas Lifeline Phone and Internet Discount calculator.

    Uses PolicyEngine's federal ``lifeline`` calculator with the KS state branch.
    Kansas layers a state supplement ($7.77/month, phone service only) on top of
    the federal benefit ($9.25/month), for a combined $17.02/month ($204.24/year).

    The KS supplement is released by PE only up to the household's ``phone_cost``
    (``min_(phone_cost, ks_supplement * MONTHS_IN_YEAR)`` in PE's ``lifeline.py``).
    ``phone_cost`` is supplied via the base ``Lifeline.pe_inputs`` (PhoneCostDependency),
    so without it every KS household would silently receive only the federal-only
    $111/year instead of $204.24/year. Mirrors the TxLifeline / WaLifeline pattern,
    adding the KS state code so PE resolves the KS supplement parameters.
    """

    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
