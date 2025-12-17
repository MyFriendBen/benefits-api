from .homebridge.calculator import MaHomeBridge
from .dhsp_afterschool.calculator import MaDhspAfterschool
from ..calc import ProgramCalculator
from .cha.calculator import Cha

ma_calculators: dict[str, type[ProgramCalculator]] = {
    "ma_homebridge": MaHomeBridge,
    "ma_cha": Cha,
    "ma_dhsp_afterschool": MaDhspAfterschool,
}
