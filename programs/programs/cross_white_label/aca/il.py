"""IL ACA premium tax credit."""

from programs.programs.cross_white_label.aca.base import Aca
import programs.framework.pe_dependencies.household as household_dependency


class IlAca(Aca):
    program_code = "il_aca"
    pe_name = "aca_ptc"
    pe_inputs = [
        *Aca.pe_inputs,
        household_dependency.IlStateCodeDependency,
        household_dependency.IlCountyDependency,
    ]
