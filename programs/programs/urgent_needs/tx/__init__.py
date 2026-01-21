from ..base import UrgentNeedFunction
from .early_intervention import EarlyIntervention
from .workforce_solutions import WorkforceSolutions
<<<<<<< HEAD
from .rewiring_america import RewiringAmerica
=======
from .law_help import LawHelp
>>>>>>> main

tx_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "tx_early_intervention": EarlyIntervention,
    "tx_workforce_solutions": WorkforceSolutions,
<<<<<<< HEAD
    "tx_rewiring_america": RewiringAmerica,
=======
    "tx_law_help": LawHelp,
>>>>>>> main
}
