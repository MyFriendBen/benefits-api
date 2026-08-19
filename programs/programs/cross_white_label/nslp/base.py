"""National School Lunch Program."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class SchoolLunch(PolicyEngineSpmCalulator):
    """
    National School Lunch Program (NSLP) — free/reduced-price school meals.

    The value is PolicyEngine's ``school_meal_net_subsidy``: the annual value of
    free/reduced meals above the full-price baseline, computed from USDA per-meal
    rates × school days × the household's K-12 children (ages 5–17, imputed by PE
    from ``age``). PAID-tier households net to $0, so eligibility is value > 0.
    ``AgeDependency`` is sent so PE can derive ``is_in_k12_school``.
    """

    program_code = "nslp"

    pe_name = "school_meal_net_subsidy"
    pe_inputs = [
        dependency.spm.SchoolMealCountableIncomeDependency,
        dependency.member.AgeDependency,
    ]
    pe_outputs = [dependency.spm.SchoolMealNetSubsidy, dependency.spm.SchoolMealTier]
