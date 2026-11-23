from programs.warnings.base import WarningCalculator


class TaxUnit(WarningCalculator):
    def eligible(self):
        return self.screen.has_members_outside_of_tax_unit()
