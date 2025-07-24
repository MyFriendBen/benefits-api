from .co import co_calculators
from .nc import nc_calculators
from .il import il_calculators
from .federal import federal_calculators
from .dev import dev_calculators
from .calc import ProgramCalculator

calculators: dict[str, type[ProgramCalculator]] = {
    **co_calculators,
    **nc_calculators,
    **il_calculators,
    **federal_calculators,
    **dev_calculators,
}
