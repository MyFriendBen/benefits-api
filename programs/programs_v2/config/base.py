"""
Base Config class for all program configurations.

Config classes define:
- What PolicyEngine inputs are needed
- What PolicyEngine outputs are needed
- Calculation period (from Program.year.period)
- Any program-specific settings
"""

from typing import List, Type
from programs.models import Program
from programs.programs_v2.policyengine.inputs.base import PolicyEngineInput
from programs.programs_v2.policyengine.outputs.base import PolicyEngineOutput


class Config:
    """
    Base configuration class for all programs.

    Subclasses should define:
    - pe_inputs: List of PolicyEngineInput classes needed
    - pe_outputs: List of PolicyEngineOutput instances needed
    - pe_period_month (optional): Specific month for output period (e.g., "01" for January)
    """

    # Override in subclasses
    pe_inputs: List[Type[PolicyEngineInput]] = []
    pe_outputs: List[PolicyEngineOutput] = []
    pe_period_month: str = None  # Optional: specific month for output period

    def __init__(self, program: Program):
        """
        Initialize config with a Program model instance.

        Args:
            program: The Program model instance containing period and other settings
        """
        self.program = program

    @property
    def period(self) -> str:
        """
        Get the calculation period from the Program model.

        Returns:
            Period string from Program.year.period (e.g., '2024')
        """
        return self.program.year.period if self.program.year else "2024"

    @property
    def output_period(self) -> str:
        """
        Get the output period for this program.

        If pe_period_month is set, returns period with month (e.g., '2024-01').
        Otherwise returns the base period (e.g., '2024').

        Returns:
            Period string, optionally with month
        """
        if self.pe_period_month:
            return f"{self.period}-{self.pe_period_month}"
        return self.period
