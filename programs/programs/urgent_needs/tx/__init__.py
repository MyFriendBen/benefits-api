from ..base import UrgentNeedFunction
from .workforce_solutions import WorkforceSolutions

tx_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {"tx_workforce_solutions": WorkforceSolutions}
