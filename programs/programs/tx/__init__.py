from .ccad.calculator import TxCcad
from ..calc import ProgramCalculator
from .ssdi.calculator import TxSsdi
from .wap.calculator import TxWap

tx_calculators: dict[str, type[ProgramCalculator]] = {
    "tx_ssdi": TxSsdi,
    "tx_ccad": TxCcad,
    "tx_wap": TxWap,
}
