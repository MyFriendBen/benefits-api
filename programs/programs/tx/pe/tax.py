from programs.programs.federal.pe.tax import Aca
import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.ctc.base import Ctc


class TxAca(Aca):
    program_code = "tx_aca"
    pe_name = "aca_ptc"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
