"""Tests for the discovery that builds the key -> class registries.

The failure mode this guards against is a registry that is quietly *incomplete*
— a program silently absent rather than an error. Two real bugs during
development produced exactly that, and both are pinned below:

- ``pkgutil.walk_packages`` recurses only through directories that have an
  ``__init__.py``, and stops at the first that does not without raising. Several
  program directories hold only a ``spec.md``, and ``nc/medicaid`` is a bare
  namespace directory, so every calculator underneath was skipped.
- Marking a class "seen" before checking whether it is a subclass meant a class
  re-exported by an earlier module was skipped at its real definition. That
  capped discovery at 115 of 235.
"""

from django.test import SimpleTestCase

from programs.framework.base import ProgramCalculator
from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.registry import DuplicateRegistryKey, _walk_classes, build
from programs.framework.tests.registry_fixtures.base import FixtureBase as _FixtureBase
from programs.framework.tests.registry_fixtures.valid.programs import (
    FixtureChildWithNoKeyOfItsOwn as _FixtureChildWithNoKeyOfItsOwn,
)
from programs.framework.tests.registry_fixtures.valid.programs import FixtureParent as _FixtureParent

_FIXTURE_PACKAGE = "programs.framework.tests.registry_fixtures.valid"
_DUPLICATE_PACKAGE = "programs.framework.tests.registry_fixtures.duplicate"


class WalkClassesTests(SimpleTestCase):
    """Discovery reaches every calculator, wherever it lives."""

    def test_finds_calculators_under_a_directory_with_no_init_file(self):
        """A spec-only or namespace directory must not hide the calculators below it.

        ``mo/head_start/`` and ``tx/liheap/`` contain only a ``spec.md``, and
        ``nc/medicaid/`` has no ``__init__.py`` of its own — the exact shape that
        made ``pkgutil.walk_packages`` stop early.
        """
        found = {c.__name__ for c in _walk_classes("programs.programs", ProgramCalculator)}

        # Lives under nc/medicaid/, a directory with no __init__.py.
        self.assertIn("CoEmergencyMedicaid", found)
        self.assertIn("NcEmergencyMedicaid", found)

    def test_finds_plain_mfb_calculators_not_only_policyengine_ones(self):
        """Both engines are discovered.

        When the seen-set was checked too early, only PolicyEngine calculators
        survived — every plain ``ProgramCalculator`` was dropped.
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

    def test_an_inherited_key_does_not_register_the_subclass(self):
        """A subclass that forgets its own key is skipped, not given its parent's.

        Registering it would either hand the parent's key to the child or raise a
        duplicate that points at the wrong file. Built against a throwaway package
        so the assertion is about `build`, not about a hand-made exception.
        """
        registry = build(_FIXTURE_PACKAGE, _FixtureBase)

        self.assertIs(registry["fixture_parent"], _FixtureParent)
        self.assertNotIn(_FixtureChildWithNoKeyOfItsOwn, registry.values())

    def test_duplicate_keys_raise_and_name_both_classes(self):
        """Two classes claiming one key is an error, and the message says which.

        This is the case `screener/views.py` used to swallow: it built
        `{p.name_abbreviated: p for p in all_programs}`, so a collision silently
        kept whichever row came last.
        """
        with self.assertRaises(DuplicateRegistryKey) as ctx:
            build(_DUPLICATE_PACKAGE, _FixtureBase)

        message = str(ctx.exception)
        self.assertIn("fixture_duplicate", message)
        self.assertIn("FirstClaimant", message)
        self.assertIn("SecondClaimant", message)


class DiscoveryMatchesTheHandMaintainedDictsTests(SimpleTestCase):
    """Discovery reproduces the hand-written dicts exactly.

    This is the argument that retiring them preserves behaviour: same keys, same
    classes, nothing missing and nothing extra. It is deliberately written against
    the real registries rather than a fixture, and it is the test to delete last —
    once the dicts are gone there is nothing left to compare against.
    """

    def test_every_key_resolves_to_the_same_class_either_way(self):
        from integrations.clients.policyengine.registry import all_calculators
        from programs.programs import calculators

        hand_maintained = {**calculators, **all_calculators}
        discovered = build("programs.programs", ProgramCalculator)

        self.assertEqual(
            set(hand_maintained) - set(discovered),
            set(),
            "a key in the dicts was not discovered — a program would silently disappear",
        )
        self.assertEqual(
            set(discovered) - set(hand_maintained),
            set(),
            "discovery found a key the dicts do not have",
        )
        self.assertEqual(hand_maintained, discovered)

    def test_the_federal_bases_states_subclass_are_not_registered(self):
        """A base with no Program row of its own must claim no key.

        ``Cdcc`` is the live example: MFB-1207 registered it directly as
        ``ks_cdcc_federal``, so when this branch added ``KsCdccFederal`` and
        ``MoCdccFederal`` the base was left holding a key two classes then claimed.
        The duplicate guard caught it, which is what it is for.
        """
        from programs.programs.federal.pe.member import Ccdf, EarlyHeadStart, HeadStart, Medicaid
        from programs.programs.federal.pe.tax import Cdcc

        for base in (Cdcc, Medicaid, HeadStart, EarlyHeadStart, Ccdf):
            with self.subTest(base=base.__name__):
                self.assertNotIn(
                    "name_abbreviated",
                    vars(base),
                    f"{base.__name__} is a base that states subclass; it must not claim a key",
                )
