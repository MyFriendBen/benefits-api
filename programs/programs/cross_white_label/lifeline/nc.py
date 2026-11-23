"""NC Lifeline."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
import programs.framework.pe_dependencies as dependency


class NcLifeline(Lifeline):
    """North Carolina carries no PolicyEngine state supplement, so the value is federal-only.

    ``NcStateCodeDependency`` is still load-bearing: ``pe_input()`` never sends
    ``state_code`` on its own, and without it PE falls back to its own default state.
    """

    program_code = "nc_lifeline"

    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]
