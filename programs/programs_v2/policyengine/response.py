"""
PolicyEngineResponse - Parses and provides access to PolicyEngine API responses.

This class encapsulates the logic for accessing data from a PolicyEngine API response,
providing a clean interface for extracting values at different unit levels.
"""

from typing import Any, Dict, List


class PolicyEngineResponse:
    """
    Wraps a PolicyEngine API response to provide convenient data access.

    The PolicyEngine response has a nested structure:
    {
        "result": {
            "people": {
                "person_id": {
                    "variable_name": {
                        "period": value
                    }
                }
            },
            "spm_units": { ... },
            "tax_units": { ... },
            "households": { ... }
        }
    }
    """

    def __init__(self, response_data: Dict[str, Any]):
        """
        Initialize a PolicyEngineResponse.

        Args:
            response_data: The raw response dictionary from PolicyEngine API
                          (should contain a 'result' key)
        """
        if "result" not in response_data:
            raise ValueError("PolicyEngine response missing 'result' key")

        self.raw_response = response_data
        self.result = response_data["result"]

    def get_member_value(self, member_id: int, variable: str, period: str) -> Any:
        """
        Get a member-level value from the response.

        Args:
            member_id: The ID of the household member
            variable: The PolicyEngine variable name (e.g., 'medicaid')
            period: The time period (e.g., '2024')

        Returns:
            The value for the specified member/variable/period, or 0 if not found
        """
        try:
            return self.result["people"][str(member_id)][variable][period]
        except (KeyError, TypeError):
            return 0

    def get_spm_value(self, variable: str, period: str) -> Any:
        """
        Get an SPM unit value from the response.

        Args:
            variable: The PolicyEngine variable name (e.g., 'snap')
            period: The time period (e.g., '2024')

        Returns:
            The value for the specified variable/period, or 0 if not found
        """
        try:
            return self.result["spm_units"]["spm_unit"][variable][period]
        except (KeyError, TypeError):
            return 0

    def get_household_value(self, variable: str, period: str) -> Any:
        """
        Get a household-level value from the response.

        Args:
            variable: The PolicyEngine variable name
            period: The time period (e.g., '2024')

        Returns:
            The value for the specified variable/period, or 0 if not found
        """
        try:
            return self.result["households"]["household"][variable][period]
        except (KeyError, TypeError):
            return 0

    def get_tax_unit_value(self, tax_unit_id: str, variable: str, period: str) -> Any:
        """
        Get a tax unit value from the response.

        Args:
            tax_unit_id: The tax unit identifier (e.g., 'tax_unit_1')
            variable: The PolicyEngine variable name
            period: The time period (e.g., '2024')

        Returns:
            The value for the specified tax unit/variable/period, or 0 if not found
        """
        try:
            return self.result["tax_units"][tax_unit_id][variable][period]
        except (KeyError, TypeError):
            return 0

    def get_unit_value(self, unit: str, sub_unit: str, variable: str, period: str) -> Any:
        """
        Get a value from any unit type (generic accessor).

        Args:
            unit: The unit type (e.g., 'people', 'spm_units', 'tax_units', 'households')
            sub_unit: The sub-unit identifier (e.g., 'person_id', 'spm_unit', 'household')
            variable: The PolicyEngine variable name
            period: The time period

        Returns:
            The value for the specified path, or 0 if not found
        """
        try:
            return self.result[unit][sub_unit][variable][period]
        except (KeyError, TypeError):
            return 0

    def get_unit_members(self, unit: str, sub_unit: str) -> List[str]:
        """
        Get the list of member IDs in a unit.

        Args:
            unit: The unit type (e.g., 'spm_units', 'tax_units', 'households')
            sub_unit: The sub-unit identifier

        Returns:
            List of member ID strings, or empty list if not found
        """
        try:
            return self.result[unit][sub_unit]["members"]
        except (KeyError, TypeError):
            return []

    def has_variable(self, unit: str, sub_unit: str, variable: str, period: str) -> bool:
        """
        Check if a variable exists in the response.

        Args:
            unit: The unit type
            sub_unit: The sub-unit identifier
            variable: The variable name
            period: The time period

        Returns:
            True if the variable exists with a non-zero value, False otherwise
        """
        try:
            value = self.result[unit][sub_unit][variable][period]
            return value is not None and value != 0
        except (KeyError, TypeError):
            return False
