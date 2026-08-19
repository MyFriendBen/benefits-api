import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.ctc.base import Ctc


class Ileitc(PolicyEngineTaxUnitCalulator):
    program_code = "il_eitc"
    pe_name = "il_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ileitc]


class Ilctc(PolicyEngineTaxUnitCalulator):
    program_code = "il_ctc"
    pe_name = "il_ctc"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ilctc]
