from ..calc import ProgramCalculator
from .ssdi.calculator import KsSsdi
from .working_healthy.calculator import KsWorkingHealthy

ks_calculators: dict[str, type[ProgramCalculator]] = {
    "ks_ssdi": KsSsdi,
    "ks_working_healthy": KsWorkingHealthy,
}
