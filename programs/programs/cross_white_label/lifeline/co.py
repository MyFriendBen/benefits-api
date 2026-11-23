"""CO Lifeline."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
import programs.framework.pe_dependencies as dependency


class CoLifeline(Lifeline):
    """Colorado carries no PolicyEngine state supplement, so the value is federal-only.

    ``CoStateCodeDependency`` is still load-bearing: ``pe_input()`` never sends
    ``state_code`` on its own, and without it PE falls back to its own default state.
    """

    program_code = "co_lifeline"

    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]
