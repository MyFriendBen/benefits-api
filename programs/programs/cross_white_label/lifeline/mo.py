"""MO Lifeline."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
import programs.framework.pe_dependencies as dependency


class MoLifeline(Lifeline):
    """
    Missouri Lifeline Phone and Internet Discount calculator.

    Uses PolicyEngine's federal ``lifeline`` calculator as-is: PE carries state
    supplements for CA, OR, TX, and KS, and Missouri matches none of them, so a
    Missouri household receives the federal benefit only.

    ``MoStateCodeDependency`` is load-bearing. ``pe_input()`` never sends
    ``state_code`` on its own, and PE's Lifeline chain branches on it for both the
    state supplement and the income limit (TX expands to 150% FPG against the
    federal 135%). Without it PE falls back to its own default state.
    """

    program_code = "mo_lifeline"

    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]
