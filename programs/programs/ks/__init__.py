from ..calc import ProgramCalculator
from .ssdi.calculator import KsSsdi

ks_calculators: dict[str, type[ProgramCalculator]] = {
    "ks_ssdi": KsSsdi,
}
