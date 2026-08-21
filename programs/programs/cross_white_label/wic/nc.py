"""NC WIC."""

from programs.programs.cross_white_label.wic.base import Wic
import programs.framework.pe_dependencies as dependency


class NcWic(Wic):
    program_code = "nc_wic"
    wic_categories = {
        "NONE": 0,
        "INFANT": 60,
        "CHILD": 60,
        "PREGNANT": 60,
        "POSTPARTUM": 60,
        "BREASTFEEDING": 60,
    }
    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]
