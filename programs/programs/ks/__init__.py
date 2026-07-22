from ..calc import ProgramCalculator
from .ssdi.calculator import KsSsdi
from .k40h.calculator import KsK40h
from .working_healthy.calculator import KsWorkingHealthy
from .promise_act.calculator import KsPromiseAct
from .lieap.calculator import KsLieap

ks_calculators: dict[str, type[ProgramCalculator]] = {
    "ks_ssdi": KsSsdi,
    "ks_k40h": KsK40h,
    "ks_working_healthy": KsWorkingHealthy,
    "ks_promise_act": KsPromiseAct,
    "ks_lieap": KsLieap,
}
