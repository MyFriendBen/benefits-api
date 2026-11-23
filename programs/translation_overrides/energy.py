from programs.programs.white_labels.cesn.util import ENERGY_EXPENSE_TYPES
from programs.translation_overrides.base import TranslationOverrideCalculator


class CesnRenter(TranslationOverrideCalculator):
    def eligible(self) -> bool:
        """
        Show for renters with no expenses
        """
        return self.screen.path == "renter" and not self.screen.has_expense(ENERGY_EXPENSE_TYPES)
