"""
SPM Unit level PolicyEngine output definitions.

These outputs represent values that PolicyEngine calculates at the SPM unit level.
"""

from .base import PolicyEngineOutput


# SNAP Output
SnapOutput = PolicyEngineOutput(
    field="snap",
    unit="spm_units",
    sub_unit="spm_unit"
)
