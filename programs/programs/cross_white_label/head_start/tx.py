"""TX Head Start."""

from programs.programs.cross_white_label.head_start.base import HeadStart
import programs.framework.pe_dependencies as dependency


class TxHeadStart(HeadStart):
    """Texas Head Start (ages 3-5) — federal ``HeadStart`` PE calculator + TX state code."""

    program_code = "tx_head_start"

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
