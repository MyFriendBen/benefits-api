import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap


# TODO: add state specific SPM calculators from PE here
# TODO: add dependency.household.WaStateCode dependency


# NOTE: here is a possible implementation of SNAP for Washington
class WaSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
