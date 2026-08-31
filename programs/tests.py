from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db.utils import IntegrityError
from django.test import SimpleTestCase, TestCase

from programs.fpl_values import MAX_MATERIALIZED_SIZE, sync_fpl_values
from programs.models import (
    _FPL_DEFAULTS,
    FederalPoveryLimit,
    FederalPovertyLimitValue,
    Program,
    _get_fpl_data,
)
from screener.models import WhiteLabel


class ProgramNameAbbreviatedNormalizationTests(TestCase):
    """Program.save() lowercases name_abbreviated so the case-sensitive key the
    calculator registry and the frontend current_benefits round-trip rely on is
    enforced at the data layer, not just by convention (MFB-720)."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    def test_new_program_lowercases_name_abbreviated(self):
        program = Program.objects.new_program(self.white_label.code, "SNAP")
        program.refresh_from_db()
        self.assertEqual(program.name_abbreviated, "snap")

    def test_save_lowercases_mixed_case_on_update(self):
        program = Program.objects.new_program(self.white_label.code, "snap")
        program.name_abbreviated = "Co_Snap"
        program.save()
        program.refresh_from_db()
        self.assertEqual(program.name_abbreviated, "co_snap")

    def test_save_leaves_already_lowercase_unchanged(self):
        program = Program.objects.new_program(self.white_label.code, "tx_snap")
        program.refresh_from_db()
        self.assertEqual(program.name_abbreviated, "tx_snap")


class FederalPovertyLimitTests(SimpleTestCase):
    """The FPL table is a module constant, so reading it must not touch the cache.

    It used to sit behind a cache whose update() opened with `return self.default`,
    leaving the ASPE API fetch below unreachable -- so the cached value was only ever
    the constant. Once the cache moved to Redis that became a network round-trip per
    read, and as_dict()/get_limit() are called ~56 times across the calculators.
    """

    def test_returns_the_table_without_touching_the_cache(self):
        with patch("programs.models.cache", create=True) as cache_mock:
            _get_fpl_data()

        self.assertFalse(cache_mock.method_calls, f"unexpected cache use: {cache_mock.method_calls}")

    def test_as_dict_makes_no_cache_calls(self):
        fpl = FederalPoveryLimit(year="2026", period="2026")

        with patch("programs.models.cache", create=True) as cache_mock:
            for _ in range(10):
                fpl.as_dict()

        self.assertFalse(cache_mock.method_calls)

    def test_identity_is_stable_across_calls(self):
        """A miss used to return the constant while a hit returned a copy.

        Callers mutating the result corrupted the constant, but only on the miss path,
        so it would have surfaced intermittently.
        """
        self.assertIs(_get_fpl_data(), _get_fpl_data())
        self.assertIs(_get_fpl_data(), _FPL_DEFAULTS)

    def test_unknown_period_still_raises_key_error(self):
        """Behaviour preserved: an unrecognised year must fail loudly, not return {}."""
        with self.assertRaises(KeyError):
            FederalPoveryLimit(year="1999", period="1999").as_dict()

    def test_get_limit_within_defined_sizes(self):
        fpl = FederalPoveryLimit(year="2026", period="2026")

        self.assertEqual(fpl.get_limit(4), _FPL_DEFAULTS["2026"][4])

    def test_get_limit_extrapolates_beyond_max_defined_size(self):
        fpl = FederalPoveryLimit(year="2026", period="2026")
        table = _FPL_DEFAULTS["2026"]
        expected = table[8] + table["additional"] * 2

        self.assertEqual(fpl.get_limit(10), expected)

    def test_every_year_defines_all_household_sizes(self):
        """Guards the constant itself -- a missing size would raise mid-screening."""
        for year, table in _FPL_DEFAULTS.items():
            with self.subTest(year=year):
                self.assertEqual(
                    sorted(k for k in table if isinstance(k, int)),
                    list(range(1, FederalPoveryLimit.MAX_DEFINED_SIZE + 1)),
                )
                self.assertIn("additional", table)


class FederalPovertyLimitValueTests(TestCase):
    """The materialized FPL table must reproduce get_limit() exactly.

    FederalPovertyLimitValue exists so SQL-only consumers (the dbt/Metabase
    analytics pipeline) can compute a percent-of-FPL band, which they cannot do
    while the thresholds live only in a Python constant. It is a mirror of
    _FPL_DEFAULTS, so the risk it introduces is drift: someone adds a year to the
    constant and the table silently keeps answering with the old one. These tests
    are what make that a CI failure instead of a wrong number on a dashboard.
    """

    def test_migration_populated_every_period_and_size(self):
        expected = len(_FPL_DEFAULTS) * MAX_MATERIALIZED_SIZE

        self.assertEqual(FederalPovertyLimitValue.objects.count(), expected)

    def test_every_row_matches_get_limit(self):
        """The mirror agrees with the calculators' own lookup, size by size."""
        for period in _FPL_DEFAULTS:
            fpl = FederalPoveryLimit(year=period, period=period)
            for size in range(1, MAX_MATERIALIZED_SIZE + 1):
                with self.subTest(period=period, household_size=size):
                    row = FederalPovertyLimitValue.objects.get(period=period, household_size=size)
                    self.assertEqual(row.annual_limit, fpl.get_limit(size))

    def test_sync_is_idempotent(self):
        counts = sync_fpl_values()

        self.assertEqual(counts, {"created": 0, "updated": 0, "deleted": 0})

    def test_sync_repairs_a_drifted_row(self):
        row = FederalPovertyLimitValue.objects.get(period="2026", household_size=4)
        row.annual_limit = 1
        row.save(update_fields=["annual_limit"])

        counts = sync_fpl_values()
        row.refresh_from_db()

        self.assertEqual(counts["updated"], 1)
        self.assertEqual(row.annual_limit, _FPL_DEFAULTS["2026"][4])

    def test_sync_removes_a_period_no_longer_in_the_constant(self):
        FederalPovertyLimitValue.objects.create(period="1999", household_size=1, annual_limit=1)

        counts = sync_fpl_values()

        self.assertEqual(counts["deleted"], 1)
        self.assertFalse(FederalPovertyLimitValue.objects.filter(period="1999").exists())

    def test_extrapolated_sizes_apply_the_additional_amount(self):
        table = _FPL_DEFAULTS["2026"]
        row = FederalPovertyLimitValue.objects.get(period="2026", household_size=10)

        self.assertEqual(row.annual_limit, table[8] + table["additional"] * 2)

    def test_duplicate_period_and_size_is_rejected(self):
        """The uniqueness constraint is what lets analytics join without fanning out."""
        with self.assertRaises(IntegrityError):
            FederalPovertyLimitValue.objects.create(period="2026", household_size=4, annual_limit=1)

    def test_command_reports_a_clean_sync(self):
        out = StringIO()

        call_command("sync_fpl_values", stdout=out)

        self.assertIn("0 created, 0 updated, 0 deleted", out.getvalue())

    def test_dry_run_reports_drift_without_writing(self):
        row = FederalPovertyLimitValue.objects.get(period="2026", household_size=4)
        row.annual_limit = 1
        row.save(update_fields=["annual_limit"])
        out = StringIO()

        call_command("sync_fpl_values", "--dry-run", stdout=out)
        row.refresh_from_db()

        self.assertIn("update 1", out.getvalue())
        self.assertEqual(row.annual_limit, 1, "dry run must not write")
