from .il_early_intervention import IlEarlyIntervention
from .il_cook_foreclosure import IlCookForeclosure
from .rentervention import Rentervention
from ..base import UrgentNeedFunction

il_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "il_early_interv": IlEarlyIntervention,
    "il_cook_foreclosure": IlCookForeclosure,
    "il_rentervention": Rentervention,
}
