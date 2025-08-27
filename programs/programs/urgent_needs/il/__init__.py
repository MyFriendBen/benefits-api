from programs.programs.urgent_needs.il.rentervention import Rentervention
from ..base import UrgentNeedFunction

il_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "il_rentervention": Rentervention,
}
