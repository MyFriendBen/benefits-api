from programs.programs.warnings.base import WarningCalculator


class EnergyCalculatorIsRenter(WarningCalculator):
    dependencies = ["energy_calculator"]

    def eligible(self) -> bool:
        return self.screen.energy_calculator.is_renter
