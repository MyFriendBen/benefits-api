"""
PolicyEngineClient - Orchestrates PolicyEngine API requests and responses.

This class handles making the actual API request and wrapping the response
for convenient access.
"""

from typing import Dict, Any, List, TYPE_CHECKING
from programs.programs.policyengine.engines import Sim, pe_engines
from screener.models import Screen
from sentry_sdk import capture_exception, capture_message
from django.conf import settings

if TYPE_CHECKING:
    from .inputs.base import PolicyEngineInput
    from .outputs.base import PolicyEngineOutput
    from .request import PolicyEngineRequest
    from .response import PolicyEngineResponse


class PolicyEngineClient:
    """
    Client for making PolicyEngine API calls.

    This class:
    1. Takes a PolicyEngineRequest and makes the API call
    2. Wraps the response in a PolicyEngineResponse for easy access
    3. Handles fallback between different PolicyEngine API methods (private/public)
    """

    def __init__(self):
        """Initialize the PolicyEngineClient."""
        self.request_payload: Dict[str, Any] = None
        self.response_json: Dict[str, Any] = None
        self._sim_instance: Sim = None

    def calculate(self, request: "PolicyEngineRequest") -> "PolicyEngineResponse":
        """
        Execute a PolicyEngine calculation request.

        This tries multiple PolicyEngine API methods (private, then public)
        and returns the first successful response.

        Args:
            request: A PolicyEngineRequest instance

        Returns:
            A PolicyEngineResponse instance

        Raises:
            RuntimeError: If all API methods fail
        """
        from .response import PolicyEngineResponse

        request_payload = request.build()
        self.request_payload = request_payload

        # Try each engine method in order (private API, then public API)
        for engine_class in pe_engines:
            try:
                sim_instance = engine_class(request_payload)
                self._sim_instance = sim_instance
                self.response_json = getattr(sim_instance, "response_json", None)

                # Wrap the response
                response = PolicyEngineResponse(self.response_json)
                return response

            except Exception as e:
                if settings.DEBUG:
                    print(f"PolicyEngine {engine_class.method_name} failed: {repr(e)}")
                capture_exception(e, level="warning")
                capture_message(
                    f"Failed to calculate eligibility with the {engine_class.method_name} method",
                    level="warning",
                )
                # Continue to next engine
                continue

        # If all engines failed, raise an error
        raise RuntimeError("All PolicyEngine API methods failed")

    def get_sim(self) -> Sim:
        """
        Get the underlying Sim instance (for backward compatibility).

        Returns:
            The Sim instance from the last successful calculation
        """
        return self._sim_instance
