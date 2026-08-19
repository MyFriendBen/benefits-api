"""TX SSI."""

from programs.programs.cross_white_label.ssi.base import Ssi
import programs.framework.pe_dependencies as dependency


class TxSsi(Ssi):
    """
    Texas SSI calculator that uses PolicyEngine's calculated benefit amounts.
    Extends the federal SSI calculator with Texas state code dependency.
    """

    program_code = "tx_ssi"

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
