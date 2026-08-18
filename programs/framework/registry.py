"""
Builds the registries that map a database key to the class implementing it.

Five kinds of row point at code by name, and the name lives in the database:
program calculators (``Program.name_abbreviated``), warning calculators
(``WarningMessage.calculator``), translation overrides
(``TranslationOverride.calculator``), urgent-need functions
(``UrgentNeedFunction.name``) and program-category cap calculators
(``ProgramCategory.calculator``).

Each class declares the key it answers to, and the registry is assembled by
walking the package at import. Nothing hand-maintains a dict, so adding a
program is one file instead of a file plus a registry edit — and a duplicate key
raises here instead of silently overwriting whichever entry lost the merge.

A class with no key is not registered. That is how abstract bases stay out:
``ProgramCalculator`` itself, the PolicyEngine entity bases, and any
family base a state subclasses.
"""

import importlib
import pathlib
from typing import Iterator, Optional, TypeVar

T = TypeVar("T")

#: Attribute a class sets to claim a database key.
KEY_ATTR = "name_abbreviated"


class DuplicateRegistryKey(Exception):
    """Two classes claim the same key.

    Raised at import rather than left to whichever class the merge order
    happened to favour. `screener/views.py` used to build
    `{p.name_abbreviated: p for p in all_programs}`, which silently kept the
    last one.
    """


def _walk_classes(package_name: str, base: type[T]) -> Iterator[type[T]]:
    """Yield every subclass of `base` defined anywhere under `package_name`.

    Imports each module, so an import error surfaces here rather than at the
    first request that needs the class.
    """
    package = importlib.import_module(package_name)
    seen: set[type] = set()

    # Walked from the filesystem rather than with pkgutil.walk_packages, which
    # recurses only through directories that have an __init__.py and stops
    # silently at the first that does not. Several program directories hold only
    # a spec.md, and nc/medicaid is a bare namespace directory — under pkgutil
    # every calculator below those was skipped without an error.
    for path in sorted(pathlib.Path(next(iter(package.__path__))).rglob("*.py")):
        parts = path.relative_to(next(iter(package.__path__))).with_suffix("").parts
        if any(p == "__pycache__" for p in parts):
            continue
        # Test modules define throwaway subclasses; a fixture that claimed a real
        # key would otherwise collide with the calculator it stands in for.
        if "tests" in parts:
            continue
        if parts[-1] == "__init__":
            parts = parts[:-1]
            if not parts:
                continue
        name = f"{package_name}." + ".".join(parts)
        try:
            module = importlib.import_module(name)
        except ImportError:
            # A directory without __init__.py is not importable as a package, but
            # its modules still are once addressed directly; anything genuinely
            # broken is caught by the repo-wide import check.
            continue
        for attr in vars(module).values():
            if not isinstance(attr, type):
                continue
            # `attr.__module__ != name` skips classes this module merely imported,
            # so a class is considered once, where it is defined. Checked before
            # `seen`, or a re-export in an earlier module marks the class seen and
            # its real definition is then skipped.
            if not (issubclass(attr, base) and attr is not base and attr.__module__ == name):
                continue
            if attr in seen:
                continue
            seen.add(attr)
            yield attr


def build(package_name: str, base: type[T], key_attr: str = KEY_ATTR) -> dict[str, type[T]]:
    """Map key -> class for every keyed subclass of `base` under `package_name`.

    A class is registered when it sets `key_attr` to a non-empty string. Bases
    and mixins leave it unset and stay out.
    """
    registry: dict[str, type[T]] = {}
    origins: dict[str, str] = {}

    for cls in _walk_classes(package_name, base):
        key: Optional[str] = getattr(cls, key_attr, None)
        if not key or not isinstance(key, str):
            continue
        # An inherited key means the subclass forgot to declare its own. Registering
        # it would hand the parent's key to the child, or raise a duplicate that
        # points at the wrong file.
        if key_attr not in vars(cls):
            continue
        if key in registry:
            raise DuplicateRegistryKey(
                f"{key!r} is claimed by both {origins[key]}.{registry[key].__name__} "
                f"and {cls.__module__}.{cls.__name__}. "
                f"Each database key must map to exactly one class."
            )
        registry[key] = cls
        origins[key] = cls.__module__

    return registry
