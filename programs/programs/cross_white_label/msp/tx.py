"""TX Medicare Savings Program."""

from programs.programs.cross_white_label.msp.base import Msp
from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class TxMsp(Msp):
    """Texas Medicare Savings Program. Federal ``Msp`` plus the TX state code and the state's
    Medicaid inputs (see ``Msp`` for why the Medicaid inputs are required)."""

    program_code = "tx_medicare_savings_program"

    pe_inputs = [
        *Msp.pe_inputs,
        dependency.household.TxStateCodeDependency,
        *Medicaid.pe_inputs,
    ]
