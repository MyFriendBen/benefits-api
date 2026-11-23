"""CO SNAP."""

from programs.programs.cross_white_label.snap.base import Snap
import programs.framework.pe_dependencies as dependency


class CoSnap(Snap):
    program_code = "co_snap"
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]
