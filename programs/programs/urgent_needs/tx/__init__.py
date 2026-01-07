from ..base import UrgentNeedFunction
from .early_intervention import EarlyIntervention
from .workforce_solutions import WorkforceSolutions
from .rewiring_america import RewiringAmerica

tx_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "tx_early_intervention": EarlyIntervention,
    "tx_workforce_solutions": WorkforceSolutions,
    "tx_rewiring_america": RewiringAmerica,
}
