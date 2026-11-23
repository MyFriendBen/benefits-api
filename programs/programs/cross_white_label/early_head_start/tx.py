"""TX Early Head Start."""

from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
import programs.framework.pe_dependencies as dependency


class TxEarlyHeadStart(EarlyHeadStart):
    """Texas Early Head Start (birth-3 / pregnant) — federal ``EarlyHeadStart`` PE calculator + TX state code."""

    program_code = "tx_early_head_start"

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
