from .ccad.calculator import TxCcad
from ..calc import ProgramCalculator
from .ssdi.calculator import TxSsdi

tx_calculators: dict[str, type[ProgramCalculator]] = {
<<<<<<< caton/mfb-676-tx-add-ssdi-social-security-disability-insurance
    "tx_ssdi": TxSsdi,
=======
    "tx_ccad": TxCcad,
>>>>>>> main
}
