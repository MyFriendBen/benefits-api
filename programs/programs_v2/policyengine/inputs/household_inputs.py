"""
Household level PolicyEngine input classes.

These inputs operate at the household unit level.
"""

from .base import PolicyEngineInput


class TxStateCodeInput(PolicyEngineInput):
    """Texas state code."""
    field = "state_code"
    unit = "households"
    sub_unit = "household"

    def value(self):
        return "TX"
