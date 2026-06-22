from programs.models import WarningMessage
from programs.programs.calc import Eligibility
from programs.util import Dependencies
from screener.models import Screen


class WarningCalculator:
    dependencies = tuple()

    def __init__(
        self, screen: Screen, warning: WarningMessage, eligibility: Eligibility, missing_dependencies: Dependencies
    ) -> None:
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
