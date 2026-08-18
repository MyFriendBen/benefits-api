"""
The custom (MFB) calculators, keyed by the ``Program`` row each one backs.

Assembled by `programs.framework.registry.build`, which walks the package and
reads the ``program_code`` every calculator declares. Adding a program means
writing the calculator; nothing here needs editing.

PolicyEngine calculators are excluded even though they subclass
``ProgramCalculator``. This registry is what `Program.eligibility()` resolves
against, and it constructs a calculator with four arguments
(``screen, program, data, missing_dependencies``) where the PolicyEngine base
takes three. They are registered in
`integrations.clients.policyengine.registry` instead. MFB-1678 tracks making the
two engines siblings so the construction difference goes away.

`calculators` is built on first access. `programs.models` imports it at module
scope, and discovery imports every calculator — including the PolicyEngine ones,
whose base imports ``Program`` back out of `programs.models`. The module-level
``__getattr__`` keeps the public name a plain mapping for callers while deferring
the walk until models has finished loading.
"""

from typing import TYPE_CHECKING, Any

from programs.framework.base import ProgramCalculator

if TYPE_CHECKING:  # pragma: no cover - import-time typing only
    calculators: dict[str, type[ProgramCalculator]]

_calculators: dict[str, type[ProgramCalculator]] | None = None


def _build_calculators() -> dict[str, type[ProgramCalculator]]:
    global _calculators
    if _calculators is None:
        # Imported here, not at module scope: both reach programs.models through
        # the PolicyEngine base class.
        from programs.framework.pe_base import PolicyEngineCalulator
        from programs.framework.registry import build

        _calculators = {
            key: cls
            for key, cls in build("programs.programs", ProgramCalculator).items()
            if not issubclass(cls, PolicyEngineCalulator)
        }
    return _calculators


def __getattr__(name: str) -> Any:
    if name == "calculators":
        return _build_calculators()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
