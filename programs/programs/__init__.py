from .calc import ProgramCalculator
from .co import co_calculators
from .dev import dev_calculators
from .federal import federal_calculators
from .il import il_calculators
from .nc import nc_calculators
from .tx import tx_calculators

calculators: dict[str, type[ProgramCalculator]] = {
    **co_calculators,
    **dev_calculators,
    **federal_calculators,
    **il_calculators,
    **nc_calculators,
    **tx_calculators,
}
