"""IL National School Lunch Program."""

from programs.programs.cross_white_label.nslp.base import SchoolLunch
import programs.framework.pe_dependencies as dependency


class IlNslp(SchoolLunch):
    program_code = "il_nslp"
    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
