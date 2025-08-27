from .il_early_intervention import IlEarlyIntervention
from .il_beacon import il_beacon
from programs.programs.urgent_needs.il.rentervention import Rentervention
from ..base import UrgentNeedFunction

il_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "il_early_interv": IlEarlyIntervention,
    "il_beacon": il_beacon,
    "il_rentervention": Rentervention,
}
