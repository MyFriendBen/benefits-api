from programs.programs.federal.pe.tax import Eitc
import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator


class TxEitc(PolicyEngineTaxUnitCalulator):
    pe_name = "eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Eitc]
