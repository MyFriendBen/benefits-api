from programs.programs.federal.pe.tax import Aca
import programs.framework.pe_dependencies as dependency


class TxAca(Aca):
    pe_name = "aca_ptc"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
