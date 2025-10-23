"""
PolicyEngineOutput - Represents PolicyEngine output variables.

This module defines PolicyEngine output variables, specifying what calculations
we want PolicyEngine to perform and return.
"""

from typing import List, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .inputs import PolicyEngineInput


class PolicyEngineOutput:
    """
    Represents a PolicyEngine output variable.

    An output variable specifies what we want PolicyEngine to calculate.
    It includes metadata about the variable and optionally lists the inputs
    required to calculate it.

    Attributes:
        field: The PolicyEngine variable name (e.g., 'snap')
        unit: The unit type (e.g., 'spm_units', 'people')
        sub_unit: The sub-unit identifier (e.g., 'spm_unit')
        required_inputs: List of PolicyEngineInput classes needed for this output
    """

    def __init__(
        self,
        field: str,
        unit: str,  # Unit type: "people", "spm_units", "households", "tax_units" (TODO: Consider Literal types)
        sub_unit: str = "",  # Sub-unit identifier: "spm_unit", "household", or "" (TODO: Consider Literal types)
        required_inputs: List[Type["PolicyEngineInput"]] = None
    ):
        """
        Initialize a PolicyEngineOutput.

        Args:
            field: The PolicyEngine variable name
            unit: The unit type ("people", "spm_units", "households", "tax_units")
            sub_unit: The sub-unit identifier ("spm_unit", "household", or "")
            required_inputs: List of PolicyEngineInput classes required to calculate this output
        """
        self.field = field
        self.unit = unit
        self.sub_unit = sub_unit
        self.required_inputs = required_inputs or []

    def __repr__(self) -> str:
        return f"PolicyEngineOutput({self.field}, unit={self.unit})"
