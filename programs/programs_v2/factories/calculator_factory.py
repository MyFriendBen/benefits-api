"""
CalculatorFactory - Creates calculator instances with dependency injection.

The factory is responsible for:
1. Maintaining a registry of available calculators
2. Instantiating calculator instances with their dependencies
3. Wiring up Config and Data instances
"""

from screener.models import Screen
from programs.models import Program
from programs.programs_v2.policyengine.response import PolicyEngineResponse
from programs.programs_v2.calculators.base import Calculator
from programs.programs_v2.calculators.snap import SnapCalculator
from programs.programs_v2.config.snap import TxSnapConfig
from programs.programs_v2.data.snap import SnapData


class CalculatorFactory:
    """
    Factory for creating calculator instances.

    The factory knows how to instantiate calculators with proper dependency injection.
    It does NOT handle PolicyEngine API calls - that's done at the integration layer.
    """

    # Registry mapping calculator IDs to their classes
    # Format: calculator_id -> (CalculatorClass, ConfigClass, DataClass)
    # calculator_id should match Program.name_abbreviated (e.g., "tx_snap", "co_snap", "ma_medicaid")
    CALCULATOR_REGISTRY = {
        "tx_snap": (SnapCalculator, TxSnapConfig, SnapData),
        # Add more calculators here as they're implemented
    }

    def create_calculator(
        self,
        screen: Screen,
        program: Program,
        pe_response: PolicyEngineResponse
    ) -> Calculator:
        """
        Create a calculator instance for a single program.

        Args:
            screen: The Screen instance
            program: The Program model instance
            pe_response: The PolicyEngineResponse from the API call

        Returns:
            Calculator instance

        Raises:
            KeyError: If program.name_abbreviated is not registered
        """
        name_abbreviated = program.name_abbreviated

        if name_abbreviated not in self.CALCULATOR_REGISTRY:
            raise KeyError(f"Calculator '{name_abbreviated}' not found in registry")

        calc_class, config_class, data_class = self.CALCULATOR_REGISTRY[name_abbreviated]

        # Create config instance
        config = config_class(program)

        # Create data instance with PE response
        data = data_class(screen, config, pe_response)

        # Create calculator instance
        calculator = calc_class(screen, program, config, data)

        return calculator

    def get_config_class(self, calculator_id: str):
        """
        Get the config class for a given calculator ID.

        Args:
            calculator_id: The calculator identifier

        Returns:
            The Config class

        Raises:
            KeyError: If calculator_id is not registered
        """
        if calculator_id not in self.CALCULATOR_REGISTRY:
            raise KeyError(f"Calculator '{calculator_id}' not found in registry")

        _, config_class, _ = self.CALCULATOR_REGISTRY[calculator_id]
        return config_class
