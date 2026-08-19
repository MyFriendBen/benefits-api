"""IL Head Start."""

from programs.programs.cross_white_label.head_start.base import HeadStart
import programs.framework.pe_dependencies.household as household_dependency


class IlHeadStart(HeadStart):
    """
    Illinois Head Start (ages 3-5). Thin wrapper on the federal ``HeadStart`` PE
    calculator that adds the IL state code; all eligibility and the per-child
    value are computed by PolicyEngine with no IL-specific variance. Early Head
    Start (birth to age 3, and pregnant women) is a separate program.
    """

    program_code = "il_head_start"

    pe_inputs = [
        *HeadStart.pe_inputs,
        household_dependency.IlStateCodeDependency,
    ]
