from .homebridge.calculator import MaHomeBridge
from .dhsp_afterschool.calculator import MaDhspAfterschool
from .door2door.calculator import MaDoorToDoor
from ..calc import ProgramCalculator
from .cha.calculator import Cha
from .cpp.calculator import MaCpp
from .middle_income_rental.calculator import MaMiddleIncomeRental

ma_calculators: dict[str, type[ProgramCalculator]] = {
    "ma_homebridge": MaHomeBridge,
    "ma_cha": Cha,
    "ma_dhsp_afterschool": MaDhspAfterschool,
    "ma_door_to_door": MaDoorToDoor,
    "ma_cpp": MaCpp,
    "ma_middle_income_rental": MaMiddleIncomeRental,
}
