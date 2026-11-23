"""TX SNAP."""

from programs.programs.cross_white_label.snap.base import Snap
import programs.framework.pe_dependencies as dependency


class TxSnap(Snap):
    program_code = "tx_snap"
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
