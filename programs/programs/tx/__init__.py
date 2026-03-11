from .ccad.calculator import TxCcad
from ..calc import ProgramCalculator

tx_calculators: dict[str, type[ProgramCalculator]] = {
    "tx_ccad": TxCcad,
}
