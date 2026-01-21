from ..base import UrgentNeedFunction
from .early_intervention import EarlyIntervention
from .workforce_solutions import WorkforceSolutions
from .here_for_texas import HereForTexas
from .law_help import LawHelp
from .central_foodbank import CentralFoodbank
from .feeding_texas import FeedingTexas
from .rewiring_america import RewiringAmerica
from .diaper_bank import NationalDiaperBankNetwork

tx_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "tx_early_intervention": EarlyIntervention,
    "tx_workforce_solutions": WorkforceSolutions,
    "tx_here_for_texas": HereForTexas,
    "tx_law_help": LawHelp,
    "tx_central_foodbank": CentralFoodbank,
    "tx_feeding_texas": FeedingTexas,
    "tx_rewiring_america": RewiringAmerica,
    "tx_diaper_bank": NationalDiaperBankNetwork,
}
