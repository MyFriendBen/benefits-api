"""MO National School Lunch Program."""

from programs.programs.cross_white_label.nslp.base import SchoolLunch
import programs.framework.pe_dependencies as dependency


class MoNslp(SchoolLunch):
    """
    Missouri National School Lunch Program (NSLP) calculator.

    Uses PolicyEngine's federal ``SchoolLunch`` calculator (pe_name
    ``school_meal_net_subsidy``) as-is. NSLP is a federal program with two federal
    income tiers — free at <=130% FPG, reduced-price at <=185% FPG — and no
    Missouri-specific variance, so the federal eligibility and value logic applies
    unchanged. Mirrors the ks_nslp / tx_nslp / il_nslp precedents.

    ``MoStateCodeDependency`` is load-bearing, not boilerplate. PolicyEngine's school
    meal tier branches on the state's universal-free-meals election, and
    ``pe_input()`` never sends ``state_code`` on its own — it is only ever supplied by
    an explicit StateCode dependency in a calculator's ``pe_inputs``. Omit it and PE
    falls back to its own default state, which *does* have universal free meals:
    verified live against PE ``current`` with a household of 2 (one 9-year-old) at
    $90,000/yr — far above the 185% FPG reduced-price limit:

        state_code=MO   -> school_meal_net_subsidy $0.00      school_meal_tier PAID
        state_code omitted -> school_meal_net_subsidy $1130.96 school_meal_tier FREE

    So without this input every Missouri household would be shown eligible for
    free meals regardless of income. ``test_spm.py`` pins it for that reason.
    """

    program_code = "mo_nslp"

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]
