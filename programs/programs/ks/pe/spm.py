import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap, SchoolLunch, Lifeline


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
