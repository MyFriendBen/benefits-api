"""Tests for programs/util.py — the Dependencies set and its malformed-value channel."""

from django.test import SimpleTestCase

from programs.util import Dependencies, MalformedValue


class TestDependenciesMalformed(SimpleTestCase):
    def test_report_malformed_keeps_the_value_structured(self):
        """`malformed` holds MalformedValue, not a pre-formatted string, so the reporter
        can group Sentry events by field name instead of by a message containing the
        value (which would be one issue per screen)."""
        deps = Dependencies()
        deps.add("income_frequency")
        deps.report_malformed("income_frequency", "fortnightly", "monthly()/yearly() cannot convert it")

        self.assertEqual(len(deps.malformed), 1)
        entry = deps.malformed[0]
        self.assertIsInstance(entry, MalformedValue)
        self.assertEqual(entry.field, "income_frequency")
        self.assertEqual(entry.value, "fortnightly")
        self.assertIn("fortnightly", entry.describe())

    def test_a_fresh_dependencies_has_no_malformed_detail(self):
        self.assertEqual(Dependencies().malformed, [])
        self.assertEqual(Dependencies({"a", "b"}).malformed, [])


class TestDependenciesUpdate(SimpleTestCase):
    """`update()` is overridden to carry malformed detail along. It is the obvious method
    to reach for, so it has to be the correct one — a separate `merge()` would just mean
    detail is silently dropped the first time someone types `update()` out of habit."""

    def test_update_carries_malformed_detail(self):
        outer = Dependencies()
        inner = Dependencies()
        inner.add("income_type")
        inner.report_malformed("income_type", "", "blank")

        outer.update(inner)

        self.assertIn("income_type", outer)
        self.assertEqual([m.field for m in outer.malformed], ["income_type"])

    def test_update_accumulates_across_several_sources(self):
        outer = Dependencies()
        for field, value in (("income_type", ""), ("expense_frequency", "hourly")):
            inner = Dependencies()
            inner.add(field)
            inner.report_malformed(field, value, "unusable")
            outer.update(inner)

        self.assertEqual(sorted(m.field for m in outer.malformed), ["expense_frequency", "income_type"])

    def test_update_accepts_multiple_arguments(self):
        """set.update takes *others; the override must not quietly drop the extras."""
        a, b = Dependencies(), Dependencies()
        a.add("income_type")
        a.report_malformed("income_type", "", "blank")
        b.add("expense_type")
        b.report_malformed("expense_type", "", "blank")

        outer = Dependencies()
        outer.update(a, b)

        self.assertEqual(outer, {"income_type", "expense_type"})
        self.assertEqual(len(outer.malformed), 2)

    def test_update_with_a_plain_set_is_fine(self):
        """Plain iterables have no `malformed`; unioning one in must not raise."""
        deps = Dependencies()
        deps.update({"county", "zipcode"})

        self.assertEqual(deps, {"county", "zipcode"})
        self.assertEqual(deps.malformed, [])

    def test_update_does_not_mutate_the_source(self):
        inner = Dependencies()
        inner.report_malformed("income_type", "", "blank")

        Dependencies().update(inner)

        self.assertEqual(len(inner.malformed), 1)
