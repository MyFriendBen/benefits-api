from programs.programs.federal.pe.tax import Eitc, Ctc
import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator


class Ileitc(PolicyEngineTaxUnitCalulator):
    pe_name = "il_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ileitc]


class Ilctc(PolicyEngineTaxUnitCalulator):
    pe_name = "il_ctc"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ilctc]
