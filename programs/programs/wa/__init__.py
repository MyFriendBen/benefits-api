from .csfp.calculator import WaCsfp
from .hcv.calculator import WaHcv
from .head_start.calculator import WaHeadStart
from .liheap.calculator import WaLiheap
from .wsos_bas.calculator import WaWsosBas
from .wsos_cts.calculator import WaWsosCts
from .wsos_grd.calculator import WaWsosGrd
from ..calc import ProgramCalculator
from .seattle_fresh_bucks.calculator import WaSeattleFreshBucks
from .senior_disabled_pte.calculator import WaSeniorDisabledPte
from .ssdi.calculator import WaSsdi
from .wic.calculator import WaWic

wa_calculators: dict[str, type[ProgramCalculator]] = {
    "wa_csfp": WaCsfp,
    "wa_hcv": WaHcv,
    "wa_head_start": WaHeadStart,
    "wa_liheap": WaLiheap,
    "wa_ssdi": WaSsdi,
    "wa_wsos_bas": WaWsosBas,
    "wa_wsos_cts": WaWsosCts,
    "wa_wsos_grd": WaWsosGrd,
    "wa_seattle_fresh_bucks": WaSeattleFreshBucks,
    "wa_senior_disabled_pte": WaSeniorDisabledPte,
    "wa_wic": WaWic,
}
