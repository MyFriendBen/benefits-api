"""NC ACA premium tax credit."""

from programs.programs.cross_white_label.aca.base import Aca
import programs.framework.pe_dependencies as dependency


class NcAca(Aca):
    program_code = "nc_aca"
    pe_name = "aca_ptc"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]
