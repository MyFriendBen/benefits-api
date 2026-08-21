"""KS SNAP."""

from programs.programs.cross_white_label.snap.base import Snap
import programs.framework.pe_dependencies as dependency


class KsSnap(Snap):
    """
    Kansas Food Assistance (SNAP) calculator.

    Uses PolicyEngine's federal SNAP calculator. SNAP is a federal program with
    no Kansas-specific calculator variance; state elections (BBCE, vehicle
    exemptions, utility regions) are keyed off the state code in PolicyEngine's
    SNAP parameters, so passing the KS state code is all that is required.
    """

    program_code = "ks_snap"

    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
