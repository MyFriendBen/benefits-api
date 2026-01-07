from ..base import UrgentNeedFunction
from .early_intervention import EarlyIntervention

tx_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "tx_early_intervention": EarlyIntervention,
}
