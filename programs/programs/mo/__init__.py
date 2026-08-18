from programs.framework.base import ProgramCalculator
from .ssdi.calculator import MoSsdi

mo_calculators: dict[str, type[ProgramCalculator]] = {
    "mo_ssdi": MoSsdi,
}
