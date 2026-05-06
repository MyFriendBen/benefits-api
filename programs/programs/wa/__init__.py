from .wsos_grd.calculator import WaWsosGrd
from ..calc import ProgramCalculator

wa_calculators: dict[str, type[ProgramCalculator]] = {
    "wa_wsos_grd": WaWsosGrd,
}
