from programs.programs.federal.pe.tax import Eitc, Ctc, Aca
import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator


class TxEitc(PolicyEngineTaxUnitCalulator):
    pe_name = "eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Eitc]


class TxCtc(PolicyEngineTaxUnitCalulator):
    pe_name = "ctc_value"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ctc]


class TxAca(Aca):
    pe_name = "aca_ptc"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
