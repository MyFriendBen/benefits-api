"""Helpers for asserting a family's contract across its registered subclasses."""

from programs.framework.pe_dependencies.household import StateCode
from integrations.clients.policyengine.registry import all_calculators


def _registered_subclasses(base: type) -> dict[str, type]:
    """Every calculator registered under a program slug that subclasses ``base``."""
    return {slug: calc for slug, calc in all_calculators.items() if isinstance(calc, type) and issubclass(calc, base)}


def _state_codes(calculator: type) -> list[type]:
    return [dep for dep in calculator.pe_inputs if isinstance(dep, type) and issubclass(dep, StateCode)]


def _distinct_state_codes(calculator: type) -> set[type]:
    """
    The distinct state codes a calculator sends.

    A set rather than a list because a state's Medicaid input bundle may already carry
    that state's code, so composing ``*Msp.pe_inputs`` with ``*XxMedicaid.pe_inputs``
    can list the same class twice. The payload builder keys by field name, so a repeat
    is inert — what matters is that exactly one *distinct* state is named.
    """
    return {dep for dep in calculator.pe_inputs if isinstance(dep, type) and issubclass(dep, StateCode)}
