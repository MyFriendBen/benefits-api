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
    Washington state-funded Food Assistance Program (FAP) for legal immigrants.

    FAP pays 100% of the federal SNAP benefit level (WAC 388-400-0050), so the
    dollar value is identical to Basic Food by design. This class reuses the
    federal SNAP PolicyEngine variable and the same inputs as `WaSnap`; there is
    deliberately no FAP-specific benefit math.

    The programs differ only in *who* qualifies. FAP serves legal immigrants
    excluded from federal Basic Food solely by immigration status: green-card
    holders aged 18 or over who have not met the five-year bar, refugees and
    asylees (removed from federal SNAP effective 2025-07-04), and lawfully
    present nonqualified aliens such as asylum applicants, TPS holders, and
    parolees. That gate is expressed in the program config's
    `legal_status_required` rather than here, matching the approach on `WaTanf`.

    The `legal_status_required` lists for `wa_fap` and `wa_snap` are mutually
    exclusive so a household is never shown the same PolicyEngine value twice.
    Green-card holders under 18 are exempt from the five-year bar
    (WAC 388-424-0020(b)(viii)) and so belong to `wa_snap`.
    """

    program_code = "wa_fap"
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
