"""
CalculatorFactory: explicit registration (DECISIONS.md D-001 -- one
.register() call per program, never auto-discovered).

Registry *values* are plain callables satisfying exactly
Calculator(screen, program, missing_dependencies) -- the real call site
(screener/views.py:424) -- with config/benefit_data already bound.
as_dict() produces something directly mergeable into a co_spm_calculators-
shaped dict (co/pe/__init__.py:28-31) for a future phase to fold into
registry.py, with zero changes needed to registry.py/views.py themselves.

functools.partial, not a dynamically-built type() subclass: the real call
site never does isinstance()/issubclass() on the result (confirmed via
direct grep of policy_engine.py/views.py/registry.py -- see DECISIONS.md
D-012), so a bare callable with the right signature is all that's required.
A synthesized subclass would need a made-up class name purely for cosmetics
and would put config/data back onto a class attribute -- exactly what D-012
moved away from.
"""

from __future__ import annotations

import functools
from typing import Callable, Optional

from programs.programs.calculators.base import ConfigurableCalculator
from programs.programs.config.loader import ConfigLayer
from programs.programs.data.loader import DataLayer


class DuplicateRegistrationError(Exception):
    pass


class CalculatorFactory:
    def __init__(self):
        self._registry: dict[str, Callable[..., ConfigurableCalculator]] = {}

    def register(
        self,
        key: str,
        config: ConfigLayer,
        *,
        calculator_cls: type[ConfigurableCalculator] = ConfigurableCalculator,
        benefit_data: Optional[DataLayer] = None,
    ) -> Callable[..., ConfigurableCalculator]:
        if key in self._registry:
            raise DuplicateRegistrationError(key)

        bound = functools.partial(calculator_cls, config=config, benefit_data=benefit_data)
        self._registry[key] = bound
        return bound

    def get(self, key: str) -> Callable[..., ConfigurableCalculator]:
        return self._registry[key]

    def as_dict(self) -> dict[str, Callable[..., ConfigurableCalculator]]:
        return dict(self._registry)
