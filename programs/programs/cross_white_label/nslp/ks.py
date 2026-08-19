"""KS National School Lunch Program."""

from programs.programs.cross_white_label.nslp.base import SchoolLunch
import programs.framework.pe_dependencies as dependency


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

    program_code = "ks_nslp"

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
