"""NC SNAP."""

from programs.programs.cross_white_label.snap.base import Snap
import programs.framework.pe_dependencies as dependency


class NcSnap(Snap):
    program_code = "nc_snap"
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]
