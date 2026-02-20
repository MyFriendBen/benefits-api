from .homebridge.calculator import MaHomeBridge
from .dhsp_afterschool.calculator import MaDhspAfterschool
from .door2door.calculator import MaDoorToDoor
from .taxi_discount.calculator import MaTaxiDiscount
from ..calc import ProgramCalculator
from .cha.calculator import Cha
from .cpp.calculator import MaCpp

ma_calculators: dict[str, type[ProgramCalculator]] = {
    "ma_homebridge": MaHomeBridge,
    "ma_cha": Cha,
    "ma_dhsp_afterschool": MaDhspAfterschool,
    "ma_door_to_door": MaDoorToDoor,
    "ma_taxi_discount": MaTaxiDiscount,
    "ma_cpp": MaCpp,
}
