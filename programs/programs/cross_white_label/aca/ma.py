"""MA ACA premium tax credit."""

from programs.programs.cross_white_label.aca.base import Aca
import programs.framework.pe_dependencies as dependency


class MaAca(Aca):
    program_code = "ma_aca"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
