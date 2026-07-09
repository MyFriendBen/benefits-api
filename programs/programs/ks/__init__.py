from ..calc import ProgramCalculator
from .ssdi.calculator import KsSsdi
from .k40h.calculator import KsK40h

ks_calculators: dict[str, type[ProgramCalculator]] = {
    "ks_ssdi": KsSsdi,
    "ks_k40h": KsK40h,
}
