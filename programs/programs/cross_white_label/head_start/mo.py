"""MO Head Start."""

from programs.programs.cross_white_label.head_start.base import HeadStart
import programs.framework.pe_dependencies as dependency


class MoHeadStart(HeadStart):
    """Missouri Head Start (ages 3-5) — federal ``HeadStart`` PE calculator + MO state code."""

    program_code = "mo_head_start"

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]
