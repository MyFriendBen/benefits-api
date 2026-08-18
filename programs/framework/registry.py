"""
Builds the registries that map a database key to the class implementing it.

Five kinds of row point at code by name, and the name lives in the database:
program calculators (``Program.name_abbreviated``), warning calculators
(``WarningMessage.calculator``), translation overrides
(``TranslationOverride.calculator``), urgent-need functions
(``UrgentNeedFunction.name``) and program-category cap calculators
(``ProgramCategory.calculator``).

Each class declares the key it answers to and `build` assembles the registry by
walking the package at import, so adding a program means writing one file. A
duplicate key raises rather than resolving to whichever class happens to be
found second.

A class declares one of two things about itself, and there is no third option:

- ``program_code`` — the ``Program.name_abbreviated`` of the row it backs. Named
  for what it is on this side of the boundary: a reference to a row, not a
  property of the class. The database column is ``name_abbreviated``; MFB-1679
  brings the two names together.
- ``abstract=True`` — it exists to be subclassed and backs no row.

Declaring neither raises. Silence would read the same whether the class is a base
or whether someone forgot the code, leaving a calculator that is written,
registered nowhere, and returns nothing. ``abstract=True`` is a class keyword read
by ``__init_subclass__`` at class creation rather than an attribute, so the answer
cannot drift from the class it describes.

A class may declare a code *and* be subclassed. ``Snap`` backs the ``snap`` row
and is inherited by seven states; fourteen classes are dual-role like that. That
is why base-versus-program cannot be inferred from whether anything subclasses a
class, and has to be declared.
"""

import importlib
import pathlib
from typing import Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")

#: Attribute a class sets to claim a database key.
KEY_ATTR = "program_code"


class UnregisteredCalculator(Exception):
    """A calculator declared neither a key nor ``abstract=True``.

    Silence is ambiguous — it reads the same whether the class is a base or whether
    someone forgot the key — so it is rejected rather than guessed at. A base says
    ``abstract=True``; a program says ``name_abbreviated``.
    """


class DuplicateRegistryKey(Exception):
    """Two classes claim the same key.

    Raised at import, so a collision surfaces at deploy rather than resolving
    silently to whichever class was found second.
    """


def is_abstract(cls: type) -> bool:
    """True when the class declared ``abstract=True`` in its definition.

    Read from ``vars()`` rather than inherited: a subclass of an abstract base is
    concrete unless it says otherwise.
    """
    return bool(vars(cls).get("_abstract", False))


def _walk_classes(package_name: str, base: type[T]) -> Iterator[type[T]]:
    """Yield every subclass of `base` defined anywhere under `package_name`.

    Imports each module, so an import error surfaces here rather than at the
    first request that needs the class.
    """
    package = importlib.import_module(package_name)
    seen: set[type] = set()

    # Walked from the filesystem rather than with pkgutil.walk_packages, which
    # recurses only through directories holding an __init__.py and stops at the
    # first that does not, without raising. Program directories are not uniformly
    # packages: some hold only a spec.md, and nc/medicaid is a bare namespace
    # directory. Everything below such a directory has to stay reachable.
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
            # so a class is considered once, at its definition. This filter runs
            # before the `seen` check: a class re-exported by an earlier module
            # must not be marked seen there, or its definition is skipped.
            if not (issubclass(attr, base) and attr is not base and attr.__module__ == name):
                continue
            if attr in seen:
                continue
            seen.add(attr)
            yield attr


def register(classes: Iterable[type[T]], key_attr: str = KEY_ATTR) -> dict[str, type[T]]:
    """Map code -> class for `classes`, rejecting anything ambiguous.

    Separate from the package walk so the rules can be exercised against a handful
    of classes rather than a directory tree.
    """
    registry: dict[str, type[T]] = {}
    origins: dict[str, str] = {}
    undeclared: list[type[T]] = []

    for cls in classes:
        # Read from vars(), not getattr: an inherited code means this subclass forgot
        # to declare its own, and registering it would hand the parent's code to the
        # child or raise a duplicate pointing at the wrong file.
        code: Optional[str] = vars(cls).get(key_attr)
        if not code or not isinstance(code, str):
            if not is_abstract(cls):
                undeclared.append(cls)
            continue
        if code in registry:
            raise DuplicateRegistryKey(
                f"{code!r} is claimed by both {origins[code]}.{registry[code].__name__} "
                f"and {cls.__module__}.{cls.__name__}. "
                f"Each database key must map to exactly one class."
            )
        registry[code] = cls
        origins[code] = cls.__module__

    if undeclared:
        listed = "\n  ".join(f"{c.__module__}.{c.__name__}" for c in sorted(undeclared, key=lambda c: c.__name__))
        raise UnregisteredCalculator(
            f"These calculators declared neither {key_attr} nor abstract=True:\n  {listed}\n"
            f"Set {key_attr} to the Program.name_abbreviated it backs, or pass "
            f"abstract=True in the class definition if it exists only to be subclassed."
        )

    return registry


def build(package_name: str, base: type[T], key_attr: str = KEY_ATTR) -> dict[str, type[T]]:
    """Map code -> class for every keyed subclass of `base` under `package_name`."""
    return register(_walk_classes(package_name, base), key_attr)
