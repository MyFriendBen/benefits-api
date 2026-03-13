from ..calc import ProgramCalculator
from .ssdi.calculator import TxSsdi

tx_calculators: dict[str, type[ProgramCalculator]] = {
    "tx_ssdi": TxSsdi,
}
