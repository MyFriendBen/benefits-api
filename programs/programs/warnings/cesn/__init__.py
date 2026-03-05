from programs.programs.warnings.base import WarningCalculator
from .renters import EnergyCalculatorIsRenter

cesn_warning_calculators: dict[str, type[WarningCalculator]] = {
    "cesn_renter": EnergyCalculatorIsRenter,
}
