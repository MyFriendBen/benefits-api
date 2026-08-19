"""
The PolicyEngine calculators, keyed by the ``Program`` row each one backs.

Assembled by `programs.framework.registry.build`, which walks the package and
reads the ``program_code`` every calculator declares. Adding a program means
writing the calculator; nothing here needs editing.

A caller that wants one PolicyEngine entity filters on the base class the
calculator inherits — ``issubclass(calc, PolicyEngineMembersCalculator)`` — rather
than reading a separate per-entity mapping. ``pe_category`` on the class is what
the request payload keys off.
"""

from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.registry import build

#: Every PolicyEngine calculator, keyed by the ``Program.name_abbreviated`` it answers to.
all_calculators: dict[str, type[PolicyEngineCalulator]] = build("programs.programs", PolicyEngineCalulator)
