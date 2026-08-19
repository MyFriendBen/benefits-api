import programs.framework.pe_dependencies as dependency
from programs.programs.federal.pe.member import Wic
from programs.programs.federal.pe.tax import Aca
from programs.programs.cross_white_label.medicaid.base import Medicaid


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


class NcAca(Aca):
    program_code = "nc_aca"
    pe_name = "aca_ptc"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]
