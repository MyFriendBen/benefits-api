from .tax_unit import TaxUnit
from .base import WarningCalculator
from .dont_show import DontShow
from .prior_tax_year import PriorTaxYear
from .co import co_warning_calculators
from .cesn import cesn_warning_calculators
from .ma import ma_warning_calculators

general_calculators: dict[str, type[WarningCalculator]] = {
    "_show": WarningCalculator,
    "_dont_show": DontShow,
    "_tax_unit": TaxUnit,
    "_prior_tax_year": PriorTaxYear,
}

specific_calculators: dict[str, type[WarningCalculator]] = {
    **co_warning_calculators,
    **cesn_warning_calculators,
    **ma_warning_calculators,
}

warning_calculators: dict[str, type[WarningCalculator]] = {**general_calculators, **specific_calculators}
