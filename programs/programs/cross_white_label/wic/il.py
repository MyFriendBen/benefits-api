"""IL WIC."""

from programs.programs.cross_white_label.wic.base import Wic
import programs.framework.pe_dependencies.household as household_dependency


class IlWic(Wic):
    program_code = "il_wic"
    wic_categories = {
        "NONE": 0,
        "INFANT": 130,
        "CHILD": 79,
        "PREGNANT": 104,
        "POSTPARTUM": 88,
        "BREASTFEEDING": 121,
    }
    pe_inputs = [
        *Wic.pe_inputs,
        household_dependency.IlStateCodeDependency,
    ]
