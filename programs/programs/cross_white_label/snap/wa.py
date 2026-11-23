"""WA SNAP."""

from programs.programs.cross_white_label.snap.base import Snap
import programs.framework.pe_dependencies as dependency


class WaSnap(Snap):
    program_code = "wa_snap"
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]


class WaFap(Snap):
    """
    Washington's state-funded food benefit for legal immigrants.

    Pays the same amount as Basic Food, so it inherits `WaSnap`'s PolicyEngine
    variable and inputs rather than defining benefit math of its own. The
    programs differ only in which immigration statuses they serve, which is
    expressed in the program config's `legal_status_required` — the same
    approach as `WaTanf`.

    See programs/programs/cross_white_label/snap/specs/wa_fap.md for eligibility.
    """

    program_code = "wa_fap"
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
