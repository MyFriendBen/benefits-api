"""KS Head Start."""

from programs.programs.cross_white_label.head_start.base import HeadStart
import programs.framework.pe_dependencies as dependency


class KsHeadStart(HeadStart):
    """
    Kansas Head Start (ages 3-5). Thin wrapper on the federal ``HeadStart`` PE
    calculator that adds the KS state code; all eligibility and the per-child
    value are computed by PolicyEngine with no KS-specific variance. Early Head
    Start (birth to age 3, and pregnant women) is a separate program.
    """

    program_code = "ks_head_start"

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
