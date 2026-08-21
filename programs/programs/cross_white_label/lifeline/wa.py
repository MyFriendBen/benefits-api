"""WA Lifeline."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
import programs.framework.pe_dependencies as dependency


class WaLifeline(Lifeline):
    program_code = "wa_lifeline"
    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
