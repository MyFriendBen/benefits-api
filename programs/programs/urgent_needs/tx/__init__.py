from ..base import UrgentNeedFunction
from .early_intervention import EarlyIntervention
from .workforce_solutions import WorkforceSolutions
from .law_help import LawHelp
from .diaper_bank import NationalDiaperBankNetwork

tx_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "tx_early_intervention": EarlyIntervention,
    "tx_workforce_solutions": WorkforceSolutions,
    "tx_law_help": LawHelp,
    "tx_diaper_bank": NationalDiaperBankNetwork,
}
