"""MA Head Start."""

from programs.programs.cross_white_label.head_start.base import HeadStart
import programs.framework.pe_dependencies as dependency


class MaHeadStart(HeadStart):
    """Massachusetts Head Start (ages 3-5) — federal ``HeadStart`` PE calculator + MA state code."""

    program_code = "ma_head_start"

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
