from .ccad.calculator import TxCcad
from ..calc import ProgramCalculator
from .hse.calculator import TxHse
from .ssdi.calculator import TxSsdi
from .wap.calculator import TxWap

tx_calculators: dict[str, type[ProgramCalculator]] = {
    "tx_ssdi": TxSsdi,
    "tx_ccad": TxCcad,
    "tx_wap": TxWap,
    "tx_hse": TxHse,
}
