"""
Base Calculator class for Programs V2.

The Calculator is responsible for:
- Determining eligibility
- Calculating benefit values
- Providing a clean public interface (.value, .eligible, .calc(), .can_calc())
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programs.models import Program
    from screener.models import Screen


class Calculator(ABC):
    """
    Base class for all benefit program calculators.

    Calculators encapsulate the business logic for determining eligibility
    and calculating benefit values. They have access to:
    - config: Program configuration (PE inputs/outputs, period)
    - data: Data access layer (Screen, PE response, computed values)
    - program: The Program model instance

    Public interface (mimics old ProgramCalculator):
    - .value: Property that returns the benefit value
    - .eligible: Property that returns whether household is eligible
    - .calc(): Method that performs the calculation
    - .can_calc(): Method that checks if calculation is possible
    """

    def __init__(self, screen: "Screen", program: "Program", config, data):
        """
        Initialize a Calculator.

        Args:
            screen: The Screen instance
            program: The Program model instance
            config: The Config instance for this program
            data: The Data instance providing access to all data sources
        """
        self.screen = screen
        self.program = program
        self.config = config
        self.data = data

        # Cached calculation results
        self._calculated = False
        self._value = None
        self._eligible = None

    @abstractmethod
    def calculate_value(self) -> int:
        """
        Calculate the benefit value.

        Subclasses must implement this method.

        Returns:
            The annual benefit value in dollars
        """
        pass

    @abstractmethod
    def calculate_eligibility(self) -> bool:
        """
        Determine eligibility.

        Subclasses must implement this method.

        Returns:
            True if eligible, False otherwise
        """
        pass

    def can_calc(self) -> bool:
        """
        Check if calculation is possible.

        Returns:
            True if we have all required data to calculate, False otherwise
        """
        # Default implementation - can be overridden
        # Check if we have a Screen and household members
        return self.screen is not None and self.screen.household_members.exists()

    def calc(self):
        """
        Perform the calculation (calculate both value and eligibility).

        This is the main entry point for performing calculations.
        Results are cached after first call.

        Returns:
            Self (for chaining)
        """
        if not self._calculated:
            self._value = self.calculate_value()
            self._eligible = self.calculate_eligibility()
            self._calculated = True

        return self

    @property
    def value(self) -> int:
        """
        Get the calculated benefit value.

        If not yet calculated, performs calculation first.

        Returns:
            The annual benefit value in dollars
        """
        if not self._calculated:
            self.calc()
        return self._value

    @property
    def eligible(self) -> bool:
        """
        Get the eligibility status.

        If not yet calculated, performs calculation first.

        Returns:
            True if eligible, False otherwise
        """
        if not self._calculated:
            self.calc()
        return self._eligible

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(program={self.program.name_abbreviated})"
