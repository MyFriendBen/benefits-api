import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap, SchoolLunch


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
