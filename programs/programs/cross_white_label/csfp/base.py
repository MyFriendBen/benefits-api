"""CSFP."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class CommoditySupplementalFoodProgram(PolicyEngineMembersCalculator):
    program_code = "csfp"
    pe_name = "commodity_supplemental_food_program"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.spm.SchoolMealCountableIncomeDependency,
    ]
    pe_outputs = [dependency.member.CommoditySupplementalFoodProgram]
