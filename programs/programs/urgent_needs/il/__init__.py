from .il_early_intervention import IlEarlyIntervention
from .il_beacon import il_beacon
from .il_cook_foreclosure import IlCookForeclosure
from .rentervention import Rentervention
from .il_foreclosure_prevention_counseling import IlEvictionHelp
from ..base import UrgentNeedFunction

il_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "il_early_interv": IlEarlyIntervention,
    "il_beacon": il_beacon,
    "il_cook_foreclosure": IlCookForeclosure,
    "il_rentervention": Rentervention,
    "il_foreclosure_prevention_counseling": IlEvictionHelp,
}
