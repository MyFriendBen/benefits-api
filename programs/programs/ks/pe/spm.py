import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap


class KsSnap(Snap):
    """
    Kansas Food Assistance (SNAP) calculator.

    Uses PolicyEngine's federal SNAP calculator. SNAP is a federal program with
    no Kansas-specific calculator variance; state elections (BBCE, vehicle
    exemptions, utility regions) are keyed off the state code in PolicyEngine's
    SNAP parameters, so passing the KS state code is all that is required.
    """

    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
