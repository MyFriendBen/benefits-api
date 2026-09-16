from programs.models import WarningMessage
from programs.framework.base import Eligibility
from programs.util import Dependencies
from screener.models import Screen


class WarningCalculator:
    dependencies = tuple()

    # Set True if `eligible()` reads ANYTHING off `self.eligibility` other than
    # `.eligible` — `eligible_members`, `household_value`, `pass_messages`,
    # `fail_messages`.
    #
    # The eligibility run (screener.views.eligibility_results) always passes a fully
    # populated `Eligibility`, so this never restricts it. It matters to callers that
    # evaluate warnings OUTSIDE that run: `screener.assistant` rebuilds a minimal
    # `Eligibility` from a `ProgramEligibilitySnapshot`, which stores only the
    # `eligible` flag, so every other attribute sits at its constructor default
    # (empty list, 0). A calculator reading one would not error — it would quietly
    # compute against zeroes and return a plausible wrong answer. This flag lets such
    # callers skip it loudly instead (see `_warning_messages` in screener.assistant).
    #
    # Scoped to the whole object rather than to `eligible_members` alone because the
    # hazard is the silent-default behaviour, which is identical for every field on it.
    needs_full_eligibility = False

    def __init__(
        self, screen: Screen, warning: WarningMessage, eligibility: Eligibility, missing_dependencies: Dependencies
    ):
        self.screen = screen
        self.warning = warning
        self.eligibility = eligibility
        self.missing_dependencies = missing_dependencies

    def calc(self) -> bool:
        """
        Returns whether or not to display the message
        """
        if not self.can_calc():
            return False

        return self.county_eligible() and self.eligible()

    def eligible(self) -> bool:
        """
        Custom requirements for whether or not to display the message
        """
        return True

    def county_eligible(self) -> bool:
        """
        Returns whether or not the screen county is in the list of eligible warning counties

        If there are no warning counties then we assume all counties are eligible
        """
        if len(self.warning.county_names) == 0:
            return True

        return self.screen.county in self.warning.county_names

    def can_calc(self) -> bool:
        """
        Returns whether or not the program can be calculated with the missing dependencies
        """
        return not self.missing_dependencies.has(*self.dependencies)
