"""
SNAP Calculator implementation.

The SNAP calculator uses PolicyEngine to determine eligibility and benefit amounts.
"""

from .base import Calculator
from programs.programs_v2.config.snap import SnapConfig
from programs.programs_v2.data.snap import SnapData
from programs.models import Program
from screener.models import Screen


class SnapCalculator(Calculator):
    """
    SNAP (Supplemental Nutrition Assistance Program) calculator.

    Uses PolicyEngine for both eligibility and benefit calculation.
    """

    def __init__(
        self,
        screen: Screen,
        program: Program,
        config: SnapConfig,
        data: SnapData
    ):
        """
        Initialize SNAP calculator.

        Args:
            screen: The Screen instance
            program: The Program model instance
            config: The SnapConfig instance
            data: The SnapData instance
        """
        super().__init__(screen, program, config, data)

    def calculate_value(self) -> int:
        """
        Calculate SNAP benefit value from PolicyEngine.

        Returns:
            Annual SNAP benefit amount (monthly amount * 12)
        """
        return self.data.snap_value()

    def calculate_eligibility(self) -> bool:
        """
        Determine SNAP eligibility.

        A household is eligible if the benefit value is greater than zero.

        Returns:
            True if eligible (value > 0), False otherwise
        """
        return self.calculate_value() > 0
