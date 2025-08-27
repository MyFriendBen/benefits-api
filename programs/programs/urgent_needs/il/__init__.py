from .il_early_intervention import IlEarlyIntervention
from ..base import UrgentNeedFunction

il_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {"il_early_interv": IlEarlyIntervention}
