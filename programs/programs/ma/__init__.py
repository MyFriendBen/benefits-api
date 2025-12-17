from .homebridge.calculator import MaHomeBridge
from ..calc import ProgramCalculator

ma_calculators: dict[str, type[ProgramCalculator]] = {
    "ma_homebridge": MaHomeBridge,
}
