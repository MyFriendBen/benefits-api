"""Tests for the shared PolicyEngine version rules (programs/programs/policyengine/versions.py).
This is the single source of truth used by the config model, the ?pe_version override
validator, and the input-gating parser."""

from django.test import SimpleTestCase

from programs.programs.policyengine import versions as v


class TestIsValidVersionNumber(SimpleTestCase):
    def test_accepts_exact_version(self) -> None:
        self.assertTrue(v.is_valid_version_number("1.715.2"))
        self.assertTrue(v.is_valid_version_number("1.800.0"))

    def test_rejects_aliases_and_garbage(self) -> None:
        for value in ("frontier", "current", "1.7", "1.715", "v1.715.2", "1.715.2-beta", "xcZX", ""):
            self.assertFalse(v.is_valid_version_number(value), value)


class TestIsValidOverride(SimpleTestCase):
    def test_accepts_aliases(self) -> None:
        self.assertTrue(v.is_valid_override("current"))
        self.assertTrue(v.is_valid_override("frontier"))

    def test_accepts_version_number(self) -> None:
        self.assertTrue(v.is_valid_override("1.715.2"))

    def test_rejects_garbage_and_typos(self) -> None:
        for value in ("banana", "fronteir", "1.7", "v1.715.2", "1.715.2 "):
            self.assertFalse(v.is_valid_override(value), value)


class TestToComparablePeVersion(SimpleTestCase):
    def test_version_number_to_tuple(self) -> None:
        self.assertEqual(v.to_comparable_pe_version("1.715.2"), (1, 715, 2))

    def test_frontier_is_latest(self) -> None:
        # frontier compares greater than any real version (satisfies any floor).
        self.assertEqual(v.to_comparable_pe_version("frontier"), v.NEWEST_VERSION)
        self.assertGreater(v.to_comparable_pe_version("frontier"), (1, 715, 2))

    def test_current_none_and_unparseable_are_none(self) -> None:
        # "current"/None/non-numeric map to None (treated as the current default model).
        for value in ("current", None, "banana"):
            self.assertIsNone(v.to_comparable_pe_version(value), value)

    def test_parser_is_lenient_validation_is_upstream(self) -> None:
        # The parser only needs a comparable tuple; it does NOT enforce MAJOR.MINOR.PATCH
        # (that's is_valid_version_number's job, applied before a value reaches here).
        # So a malformed-but-numeric "1.7" still parses to (1, 7).
        self.assertEqual(v.to_comparable_pe_version("1.7"), (1, 7))
        self.assertFalse(v.is_valid_version_number("1.7"))
