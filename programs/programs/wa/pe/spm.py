import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Lifeline, Snap


class WaLifeline(Lifeline):
    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]


class WaSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
