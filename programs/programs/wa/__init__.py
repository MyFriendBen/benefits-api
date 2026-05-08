from .csfp.calculator import WaCsfp
from .lifeline.calculator import WaLifeline
from .wsos_bas.calculator import WaWsosBas
from .wsos_cts.calculator import WaWsosCts
from .wsos_grd.calculator import WaWsosGrd
from ..calc import ProgramCalculator
from .seattle_fresh_bucks.calculator import WaSeattleFreshBucks
from .ssdi.calculator import WaSsdi

wa_calculators: dict[str, type[ProgramCalculator]] = {
    "wa_csfp": WaCsfp,
    "wa_lifeline": WaLifeline,
    "wa_ssdi": WaSsdi,
    "wa_wsos_bas": WaWsosBas,
    "wa_wsos_cts": WaWsosCts,
    "wa_wsos_grd": WaWsosGrd,
    "wa_seattle_fresh_bucks": WaSeattleFreshBucks,
}
