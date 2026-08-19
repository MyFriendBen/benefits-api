"""Tests for the discovery that builds the key -> class registries.

The failure these guard against is a registry that is quietly *incomplete* — a
program absent rather than an error — so the assertions are about reach: that
discovery finds calculators wherever they live, and finds them once.

Two properties of the walk are load-bearing and easy to break:

- It walks the filesystem rather than using ``pkgutil.walk_packages``, which
  recurses only through directories holding an ``__init__.py``. Program
  directories are not uniformly packages: some hold only a ``spec.md``, and
  ``nc/medicaid`` is a bare namespace directory.
- It filters on where a class is *defined* before marking it seen, so a class
  re-exported by another module is still found at its definition.
"""

import importlib
from unittest import mock

from django.test import SimpleTestCase

from programs.framework.base import ProgramCalculator
from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.registry import (
    _module_names,
    DuplicateRegistryKey,
    UnregisteredCalculator,
    _walk_classes,
    build,
    is_abstract,
    register,
)


class WalkClassesTests(SimpleTestCase):
    """Discovery reaches every calculator, wherever it lives."""

    def test_finds_calculators_under_a_directory_with_no_init_file(self):
        """A spec-only or namespace directory must not hide the calculators below it.

        ``mo/head_start/`` and ``tx/liheap/`` contain only a ``spec.md``, and
        ``nc/medicaid/`` has no ``__init__.py`` of its own. A package-based walk
        stops at directories like these without raising.
        """
        found = {c.__name__ for c in _walk_classes("programs.programs", ProgramCalculator)}

        # Lives under nc/medicaid/, a directory with no __init__.py.
        self.assertIn("CoEmergencyMedicaid", found)
        self.assertIn("NcEmergencyMedicaid", found)

    def test_finds_plain_mfb_calculators_not_only_policyengine_ones(self):
        """Both engines are discovered.

        Custom calculators are the ones at risk here: they are re-exported through
        state ``__init__`` modules, so a walk that marks a class seen before
        checking where it was defined finds only the PolicyEngine half.
        """
        found = list(_walk_classes("programs.programs", ProgramCalculator))
        mfb = [c for c in found if not issubclass(c, PolicyEngineCalulator)]
        pe = [c for c in found if issubclass(c, PolicyEngineCalulator)]

        self.assertGreater(len(mfb), 50, "no plain MFB calculators discovered")
        self.assertGreater(len(pe), 50, "no PolicyEngine calculators discovered")

    def test_a_class_is_yielded_once_even_when_re_exported(self):
        """``Ctc`` is imported by several state modules but defined in one."""
        found = list(_walk_classes("programs.programs", ProgramCalculator))

        self.assertEqual(len(found), len(set(found)), "a class was yielded more than once")

    def test_skips_test_modules(self):
        """Fixtures in test modules must not enter the registry.

        A throwaway subclass that claimed a real key would collide with the
        calculator it stands in for.
        """
        modules = {c.__module__ for c in _walk_classes("programs.programs", ProgramCalculator)}

        self.assertFalse(
            [m for m in modules if ".tests" in m],
            "discovery reached a test module",
        )


class BuildTests(SimpleTestCase):
    """Keys are claimed explicitly, and collisions are loud."""

    def test_unkeyed_classes_are_not_registered(self):
        """Abstract bases stay out by declaring no key.

        ``HeadStart``, ``Medicaid``, ``Ccdf`` and friends exist only to be
        subclassed and have no ``Program`` row of their own.
        """
        registry = build("programs.programs", ProgramCalculator)

        self.assertNotIn("", registry)
        self.assertTrue(all(k for k in registry), "an empty key was registered")

    def test_an_inherited_code_does_not_register_the_subclass(self):
        """A subclass claims its own code or none; it never inherits one.

        Registering on an inherited code would either hand the parent's row to the
        child or raise a duplicate naming the wrong file.
        """

        class Parent(ProgramCalculator):
            program_code = "registry_test_parent"

        class Child(Parent, abstract=True):
            pass

        registry = register([Parent, Child])

        self.assertIs(registry["registry_test_parent"], Parent)
        self.assertNotIn(Child, registry.values())

    def test_duplicate_keys_raise_and_name_both_classes(self):
        """Two classes claiming one code is an error, and the message says which.

        A collision has no correct silent resolution — either class could be the one
        a row means — so it raises with both names in the message.
        """

        class FirstClaimant(ProgramCalculator):
            program_code = "registry_test_duplicate"

        class SecondClaimant(ProgramCalculator):
            program_code = "registry_test_duplicate"

        with self.assertRaises(DuplicateRegistryKey) as ctx:
            register([FirstClaimant, SecondClaimant])

        message = str(ctx.exception)
        self.assertIn("registry_test_duplicate", message)
        self.assertIn("FirstClaimant", message)
        self.assertIn("SecondClaimant", message)


class RegistryCoversEveryCalculatorTests(SimpleTestCase):
    """Every calculator in the tree reaches the registry, and nothing else does.

    Written against the real registries rather than a fixture: the value is in
    catching a calculator that stops being discoverable, which a fixture cannot
    see.
    """

    def test_the_two_engine_registries_partition_every_discovered_calculator(self):
        """The custom and PolicyEngine registries together cover the whole tree.

        Each is a filtered view of the same walk, so a calculator missing from both
        means discovery stopped reaching it, and a calculator in both means the
        engine split is wrong.
        """
        from integrations.clients.policyengine.registry import all_calculators
        from programs.programs import calculators

        published = {**calculators, **all_calculators}
        discovered = build("programs.programs", ProgramCalculator)

        self.assertEqual(
            set(discovered) - set(published),
            set(),
            "a discovered calculator reaches neither registry, so nothing can resolve it",
        )
        self.assertEqual(
            set(published) - set(discovered),
            set(),
            "a registry holds a code discovery does not find",
        )
        self.assertEqual(
            set(calculators) & set(all_calculators),
            set(),
            "a calculator is registered as both custom and PolicyEngine",
        )

    def test_the_federal_bases_states_subclass_are_not_registered(self):
        """A base with no Program row of its own claims no code.

        The temptation is to register a base directly under whichever state slug
        first needs it — ``Cdcc`` under ``ks_cdcc_federal``, say. It reads as
        harmless while one state uses it and breaks when a second arrives, because
        the base and the new state's subclass then claim the same code.
        """
        from programs.programs.federal.pe.member import Ccdf, EarlyHeadStart, HeadStart, Medicaid
        from programs.programs.federal.pe.tax import Cdcc

        for base in (Cdcc, Medicaid, HeadStart, EarlyHeadStart, Ccdf):
            with self.subTest(base=base.__name__):
                self.assertNotIn(
                    "program_code",
                    vars(base),
                    f"{base.__name__} is a base that states subclass; it must not claim a code",
                )


class AbstractDeclarationTests(SimpleTestCase):
    """A class says what it is; nothing is inferred.

    Base-versus-program cannot be read off the data — a calculator with no
    ``Program`` row is normal (written but not configured yet) and a row with no
    calculator is normal (tracking-only). It cannot be inferred from whether
    anything subclasses the class either: ``Chip`` is a base with zero subclasses,
    and fourteen classes are both keyed and subclassed. So each class declares.
    """

    def test_abstract_is_not_inherited(self):
        """A subclass of an abstract base is concrete unless it says otherwise.

        This is the common case — every state subclass of ``HeadStart`` is a real
        program — so it must be the default.
        """

        class Base(ProgramCalculator, abstract=True):
            pass

        class Child(Base):
            program_code = "abstract_test_child"

        self.assertTrue(is_abstract(Base))
        self.assertFalse(is_abstract(Child))

    def test_declaring_neither_a_key_nor_abstract_raises(self):
        """Silence is ambiguous, so it is rejected rather than guessed at."""

        class DeclaredNothing(ProgramCalculator):
            pass

        with self.assertRaises(UnregisteredCalculator) as ctx:
            register([DeclaredNothing])

        message = str(ctx.exception)
        self.assertIn("DeclaredNothing", message)
        self.assertIn("abstract=True", message)

    def test_a_keyed_class_may_also_be_subclassed(self):
        """Being a base and being a program are not mutually exclusive.

        ``Snap`` backs the ``snap`` row and is inherited by seven states. Fourteen
        classes are dual-role like that, which is why "is it a base?" cannot be
        inferred from whether anything subclasses it.
        """
        from programs.programs.federal.pe.spm import Snap

        registry = build("programs.programs", ProgramCalculator)

        self.assertIs(registry["snap"], Snap)
        self.assertFalse(is_abstract(Snap))
        self.assertGreater(
            len(
                [
                    c
                    for c in _walk_classes("programs.programs", ProgramCalculator)
                    if issubclass(c, Snap) and c is not Snap
                ]
            ),
            1,
        )

    def test_the_family_bases_declare_themselves_abstract(self):
        from programs.programs.federal.pe.member import Ccdf, Chip, EarlyHeadStart, HeadStart, Medicaid, Msp
        from programs.programs.federal.pe.tax import Aca, Cdcc

        for cls in (Medicaid, Chip, HeadStart, EarlyHeadStart, Ccdf, Msp, Aca, Cdcc):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(is_abstract(cls), f"{cls.__name__} backs no Program row")


class ModuleWalkTests(SimpleTestCase):
    """What the walk includes, and what it must not."""

    def _names(self):
        package = importlib.import_module("programs.programs")
        return list(_module_names("programs.programs", package))

    def test_no_test_module_is_walked(self):
        """A test module's throwaway subclasses must not reach the registry.

        One claiming a real code would collide with the calculator it stands in for,
        and the collision would name a test file. Test code appears as ``tests.py``,
        ``test_x.py`` and ``tests/test_x.py``; all three are excluded.
        """
        leaked = [name for name in self._names() if ".tests" in name or name.rsplit(".", 1)[-1].startswith("test_")]

        self.assertEqual(leaked, [], "a test module reached the walk")

    def test_a_module_that_cannot_be_imported_raises(self):
        """An unimportable module must not quietly shrink the registry.

        Swallowing the error would drop that module's calculators and leave no trace
        — a program written, registered nowhere, returning nothing. Asserted by
        making one real module unimportable and checking the walk stops, rather than
        by pointing at a package that does not exist: that would fail on the
        package import and never reach the per-module loop this guards.
        """
        real_import = importlib.import_module
        broken = "programs.programs.tx.pe.tax"

        def fail_on_one(name, *args, **kwargs):
            if name == broken:
                raise ModuleNotFoundError(f"No module named {name!r}")
            return real_import(name, *args, **kwargs)

        with mock.patch.object(importlib, "import_module", side_effect=fail_on_one):
            with self.assertRaises(ModuleNotFoundError):
                list(_walk_classes("programs.programs", ProgramCalculator))

    def test_every_directory_on_the_package_path_is_walked(self):
        """``__path__`` is a list, and only reading its first entry would silently
        skip whole directories of a namespace package."""
        package = importlib.import_module("programs.programs")
        names = self._names()

        for entry in package.__path__:
            with self.subTest(entry=entry):
                self.assertTrue(names, f"nothing walked under {entry}")
