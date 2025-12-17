from .homebridge.calculator import MaHomeBridge
from ..calc import ProgramCalculator
from .cha.calculator import Cha

ma_calculators: dict[str, type[ProgramCalculator]] = {
    "ma_homebridge": MaHomeBridge,
    "ma_cha": Cha,
}
