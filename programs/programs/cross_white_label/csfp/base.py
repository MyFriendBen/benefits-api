"""CSFP."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class CommoditySupplementalFoodProgram(PolicyEngineMembersCalculator):
    """
    Federal CSFP. PolicyEngine decides it with::

        age >= 60 & income_test & county_eligible

    ``income_test`` is ``school_meal_fpg_ratio`` at or below 150% FPG (TX: 130%).
    ``county_eligible`` gates MA; TX and CO have no county gate.
    Income is ``CsfpCountableIncomeDependency``.
    """

    program_code = "csfp"
    pe_name = "commodity_supplemental_food_program"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.spm.CsfpCountableIncomeDependency,
    ]
    pe_outputs = [dependency.member.CommoditySupplementalFoodProgram]
