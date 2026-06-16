from ..calc import ProgramCalculator
from .ssdi.calculator import KsSsdi
from .kancare_hcbs.calculator import KsKancareHcbs

ks_calculators: dict[str, type[ProgramCalculator]] = {
    "ks_ssdi": KsSsdi,
    "ks_kancare_hcbs": KsKancareHcbs,
}
