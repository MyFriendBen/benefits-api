from .ccad.calculator import TxCcad
from ..calc import ProgramCalculator
from .fpp.calculator import TxFpp
from .hcv.calculator import TxHcv
from .hse.calculator import TxHse
from .htw.calculator import TxHtw
from .ssdi.calculator import TxSsdi
from .wap.calculator import TxWap

tx_calculators: dict[str, type[ProgramCalculator]] = {
    "tx_ssdi": TxSsdi,
    "tx_ccad": TxCcad,
    "tx_wap": TxWap,
    "tx_hse": TxHse,
    "tx_htw": TxHtw,
    "tx_fpp": TxFpp,
    "tx_hcv": TxHcv,
}
