import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap, SchoolLunch, Tanf


class TxSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
