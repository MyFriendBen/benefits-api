"""
Base Data class for all program data layers.

The Data class provides access to all data sources needed by calculators:
- Screen data (household information)
- PolicyEngine API response data
- Config settings

This acts as a facade over multiple data sources.
"""

from screener.models import Screen
from programs.programs_v2.policyengine.response import PolicyEngineResponse
from programs.programs_v2.config.base import Config


class Data:
    """
    Base data access layer for all calculators.

    Provides convenient access to:
    - Screen data (household information)
    - PolicyEngine response values
    - Configuration settings

    Subclasses should implement program-specific data access methods.
    """

    def __init__(
        self,
        screen: Screen,
        config: Config,
        pe_response: PolicyEngineResponse
    ):
        """
        Initialize data layer.

        Args:
            screen: The Screen instance with household data
            config: The Config instance for this program
            pe_response: The PolicyEngineResponse from the API call
        """
        self.screen = screen
        self.config = config
        self.pe_response = pe_response
