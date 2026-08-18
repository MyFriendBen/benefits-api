from programs.programs.federal.pe.tax import Eitc, Ctc
import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator


class Ileitc(PolicyEngineTaxUnitCalulator):
    name_abbreviated = "il_eitc"
    pe_name = "il_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ileitc]


class Ilctc(PolicyEngineTaxUnitCalulator):
    name_abbreviated = "il_ctc"
    pe_name = "il_ctc"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ilctc]
