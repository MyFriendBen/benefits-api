"""MA SNAP."""

from programs.programs.cross_white_label.snap.base import Snap
import programs.framework.pe_dependencies as dependency


class MaSnap(Snap):
    program_code = "ma_snap"
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
