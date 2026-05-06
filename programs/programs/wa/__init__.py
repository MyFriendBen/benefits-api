from .wsos_grd.calculator import WaWsosGrd
from ..calc import ProgramCalculator
from .ssdi.calculator import WaSsdi

wa_calculators: dict[str, type[ProgramCalculator]] = {
    "wa_ssdi": WaSsdi,
    "wa_wsos_grd": WaWsosGrd
}
