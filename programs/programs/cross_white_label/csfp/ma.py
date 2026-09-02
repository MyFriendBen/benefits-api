"""MA CSFP."""

from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
import programs.framework.pe_dependencies as dependency


class MaCsfp(CommoditySupplementalFoodProgram):
    program_code = "ma_csfp"
    pe_inputs = [
        *CommoditySupplementalFoodProgram.pe_inputs,
        dependency.household.MaStateCodeDependency,
        dependency.household.MaCountyDependency,
    ]
