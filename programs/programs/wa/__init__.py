from .wsos_grd.calculator import WaWsosGrd
from ..calc import ProgramCalculator
from .seattle_fresh_bucks.calculator import WaSeattleFreshBucks

wa_calculators: dict[str, type[ProgramCalculator]] = {
    "wa_seattle_fresh_bucks": WaSeattleFreshBucks,
    "wa_wsos_grd": WaWsosGrd,
}
