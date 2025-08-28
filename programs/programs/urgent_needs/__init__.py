from .base import UrgentNeedFunction
from .co import co_urgent_need_functions
from .ma import ma_urgent_need_functions
from .il import il_urgent_need_functions


urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    **co_urgent_need_functions,
    **ma_urgent_need_functions,
    **il_urgent_need_functions,
}
