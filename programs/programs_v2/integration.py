"""
Integration layer between Programs V2 and the rest of the application.

This module handles:
1. PolicyEngine API orchestration (batching requests for multiple calculators)
2. Calculator instantiation via the factory
3. Providing a clean interface for the existing system

This is the entry point for using V2 calculators.
"""

from typing import Dict
from screener.models import Screen
from programs.models import Program
from .policyengine import (
    PolicyEngineClient,
    PolicyEngineRequest,
)
from .factories.calculator_factory import CalculatorFactory
from .calculators.base import Calculator


def calculate_eligibility(
    screen: Screen,
    programs: Dict[str, Program]
) -> Dict[str, Calculator]:
    """
    Calculate eligibility for multiple programs in a single PolicyEngine API call.

    This is the main entry point for using V2 calculators. It:
    1. Creates Config instances for all calculators
    2. Makes a single batched PE API call with all configs
    3. Instantiates calculators with the PE response
    4. Returns calculator instances (call .calc() on them to get results)

    Args:
        screen: The Screen instance containing household data
        programs: Dict mapping calculator_id to Program model instances
                 calculator_id should be Program.name_abbreviated (e.g., "tx_snap", "ma_medicaid")
                 Example: {'tx_snap': <Program>, 'ma_medicaid': <Program>}

    Returns:
        Dict mapping calculator_id to Calculator instances
        Each calculator has .value, .eligible, .calc(), .can_calc() methods

    Example:
        >>> programs = {'tx_snap': snap_program}
        >>> calculators = calculate_eligibility(screen, programs)
        >>> snap_calc = calculators['tx_snap']
        >>> snap_calc.calc()
        >>> print(f"Eligible: {snap_calc.eligible}, Value: ${snap_calc.value}")
    """
    factory = CalculatorFactory()

    # Step 1: Create Config instances for all calculators
    configs = []

    for name_abbreviated, program in programs.items():
        try:
            # Get the config class from the factory registry
            config_class = factory.get_config_class(name_abbreviated)

            # Create config instance
            config = config_class(program)
            configs.append(config)

        except KeyError:
            # Calculator not registered, skip it
            continue

    # Step 2: Make single PolicyEngine API call with all configs
    if not configs:
        return {}

    pe_client = PolicyEngineClient()
    request = PolicyEngineRequest(screen, configs)
    pe_response = pe_client.calculate(request)

    # Step 3: Instantiate calculators with the PE response
    calculators = {}
    for name_abbreviated, program in programs.items():
        try:
            calculator = factory.create_calculator(screen, program, pe_response)
            calculators[name_abbreviated] = calculator
        except KeyError:
            # Calculator not registered, skip it
            continue

    return calculators
