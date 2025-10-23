"""
SNAP Data class.

The Data class provides access to all data sources needed by the SNAP calculator:
- Screen data (household information)
- PolicyEngine API response data
- Config settings

This acts as a facade over multiple data sources.
"""

from programs.programs_v2.config.snap import SnapConfig
from .base import Data


class SnapData(Data):
    """
    Data access layer for SNAP calculator.

    Provides SNAP-specific data access methods.
    """

    # Type hint the config for better IDE support
    config: SnapConfig

    def snap_value(self) -> int:
        """
        SNAP benefit value from PolicyEngine.

        Returns:
            Annual SNAP benefit amount from PolicyEngine
        """
        # SNAP uses specific output period (e.g., '2024-01')
        period = self.config.output_period
        monthly_value = self.pe_response.get_spm_value("snap", period)

        # Convert monthly to annual
        return int(monthly_value) * 12
