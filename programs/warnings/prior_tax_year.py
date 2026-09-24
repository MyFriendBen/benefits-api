from django.utils import timezone

from programs.warnings.base import WarningCalculator


class PriorTaxYear(WarningCalculator):
    """Show a warning only when the program's results are for last year's taxes.

    The message names the year through the `{priorYear}` placeholder, which rolls over on
    January 1. A program's configured year doesn't roll over with it, so this checks the
    two agree: a warning saying "the 2026 tax year" must never appear on results that
    were calculated for 2025. Today's date is used, as the results page does, not a
    screen's frozen reference date.
    """

    def eligible(self) -> bool:
        if self.program is None or self.program.year is None:
            return False

        try:
            program_year = int(self.program.year.period)
        except (TypeError, ValueError):
            return False

        return program_year == timezone.localdate().year - 1
