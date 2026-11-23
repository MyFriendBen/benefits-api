from programs.warnings.base import WarningCalculator


class DontShow(WarningCalculator):
    def eligible(self) -> bool:
        return False
