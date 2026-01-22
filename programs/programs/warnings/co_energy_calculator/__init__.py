from programs.programs.warnings.base import WarningCalculator
from .renters import EnergyCalculatorIsRenter

co_energy_calculator_warning_calculators: dict[str, type[WarningCalculator]] = {
    "co_energy_calculator_renter": EnergyCalculatorIsRenter,
}
