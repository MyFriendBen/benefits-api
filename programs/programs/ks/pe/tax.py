from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
from programs.programs.federal.pe.tax import Eitc
import programs.programs.policyengine.calculators.dependencies as dependency


class Kseitc(PolicyEngineTaxUnitCalulator):
    pe_name = "ks_total_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Kseitc]
