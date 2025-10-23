"""
PolicyEngineInput - Base class for PolicyEngine input variables.

This module defines PolicyEngine input variables independently, with each input
knowing its variable name, unit type, and how to calculate its value from Screen data.
"""

from typing import List, Tuple, Union
from screener.models import Screen, HouseholdMember
from abc import ABC, abstractmethod


class PolicyEngineInput(ABC):
    """
    Base class for all PolicyEngine input variables.

    Each input variable knows:
    1. Its PolicyEngine variable name (field)
    2. Its unit type (people, spm_units, households, tax_units)
    3. How to calculate its value from Screen data
    4. What Screen fields it depends on

    Subclasses should implement the `value()` method to define calculation logic.
    """

    # Class attributes to be overridden by subclasses
    # TODO: Consider using strict typing on unit, sub_unit, and dependencies
    field: str = ""  # PolicyEngine variable name
    unit: str = ""  # Unit type: "people", "spm_units", "households", "tax_units"
    sub_unit: str = ""  # Sub-unit identifier: "spm_unit", "household", or ""
    dependencies: Tuple[str, ...] = ()  # Screen field dependencies

    def __init__(
        self,
        screen: Screen,
        members: Union[List[HouseholdMember], HouseholdMember],
        relationship_map: dict
    ):
        """
        Initialize a PolicyEngineInput.

        Args:
            screen: The Screen instance containing household data
            members: List of HouseholdMember instances or a single HouseholdMember
            relationship_map: Dictionary mapping member relationships
        """
        self.screen = screen
        # Normalize to list for consistency
        if isinstance(members, HouseholdMember):
            self.members = [members]
            self.member = members  # For member-level inputs
        else:
            self.members = members
            self.member = None

        self.relationship_map = relationship_map

    @abstractmethod
    def value(self):
        """
        Calculate the input value from Screen data.

        Returns:
            The value to send to PolicyEngine for this variable
        """
        pass

    def can_calculate(self) -> bool:
        """
        Check if all required dependencies are available.

        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        # Default implementation - can be overridden
        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.field}, unit={self.unit})"
