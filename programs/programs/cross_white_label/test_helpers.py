"""Assertions over every registered subclass of a family's base.

A family declares its contract once on the base, and each white label's subclass is
expected to add only its own state's inputs. The subclass set is resolved from the
registry rather than a hand-listed tuple, so a newly registered white label is
covered without editing the test.
"""

from programs.framework.pe_dependencies.household import StateCode


def registered_subclasses(base: type) -> dict[str, type]:
    """Every calculator registered under a program slug that subclasses ``base``."""
    # Imported here, not at module scope: this module sits under programs.programs,
    # which the registry builds by walking, so a module-level import would have the
    # registry import itself.
    from integrations.clients.policyengine.registry import all_calculators

    return {slug: calc for slug, calc in all_calculators.items() if isinstance(calc, type) and issubclass(calc, base)}


def state_codes(calculator: type) -> list[type]:
    return [dep for dep in calculator.pe_inputs if isinstance(dep, type) and issubclass(dep, StateCode)]


def distinct_state_codes(calculator: type) -> set[type]:
    """
    The distinct state codes a calculator sends.

    A set rather than a list because a state's Medicaid input bundle may already carry
    that state's code, so composing ``*Msp.pe_inputs`` with ``*XxMedicaid.pe_inputs``
    can list the same class twice. The payload builder keys by field name, so a repeat
    is inert — what matters is that exactly one *distinct* state is named.
    """
    return {dep for dep in calculator.pe_inputs if isinstance(dep, type) and issubclass(dep, StateCode)}
