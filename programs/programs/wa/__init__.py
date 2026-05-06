from .csfp.calculator import WaCsfp
from .wsos_grd.calculator import WaWsosGrd
from ..calc import ProgramCalculator
from .ssdi.calculator import WaSsdi

wa_calculators: dict[str, type[ProgramCalculator]] = {
    "wa_csfp": WaCsfp,
    "wa_ssdi": WaSsdi,
    "wa_wsos_grd": WaWsosGrd,
}
