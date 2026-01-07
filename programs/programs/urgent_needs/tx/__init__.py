from ..base import UrgentNeedFunction
from .early_intervention import EarlyIntervention
from .feeding_texas import FeedingTexas

tx_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "tx_early_intervention": EarlyIntervention,
    "tx_feeding_texas": FeedingTexas,
}
