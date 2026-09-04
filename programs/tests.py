from importlib import import_module
from io import StringIO
from unittest.mock import patch

from django.apps import apps as global_apps
from django.core.management import call_command
from django.db.utils import IntegrityError
from django.test import SimpleTestCase, TestCase

from programs.fpl_values import MAX_MATERIALIZED_SIZE, limits_for_period, sync_fpl_values
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

    These verify that sync_fpl_values() produces a table matching get_limit().
    They deliberately do NOT claim to catch a given environment drifting out of
    sync -- CI builds a fresh database and syncs it here, so it can never observe
    prod's state. Keeping prod current is the deploy hook's job (see the Sync FPL
    values step in .github/actions/heroku-migrations), with
    `sync_fpl_values --dry-run` available as a drift check that exits non-zero.

    setUp syncs rather than relying on migration 0173: pytest.ini runs with
    --nomigrations, so pytest-django builds the schema from the models and never
    executes a RunPython. The migration's own populate() is covered separately.
    """

    def setUp(self):
        sync_fpl_values()

    def test_sync_populates_every_period_and_size(self):
        expected = len(_FPL_DEFAULTS) * MAX_MATERIALIZED_SIZE

        self.assertEqual(FederalPovertyLimitValue.objects.count(), expected)

    def test_migration_populate_fills_the_table(self):
        """Covers migration 0171's RunPython, which --nomigrations skips.

        This is what fills the table on a real deploy, so it needs a test that
        does not depend on the migration runner having run.
        """
        expected = len(_FPL_DEFAULTS) * MAX_MATERIALIZED_SIZE
        FederalPovertyLimitValue.objects.all().delete()
        migration = import_module("programs.migrations.0173_federal_poverty_limit_value")

        migration.populate(global_apps, None)

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

    def test_expanding_a_table_with_no_sizes_raises(self):
        """defined[-1] would otherwise be an IndexError on a malformed table."""
        with self.assertRaises(ValueError):
            limits_for_period({"additional": 5_000})

    def test_command_reports_a_clean_sync(self):
        out = StringIO()

        call_command("sync_fpl_values", stdout=out)

        self.assertIn("0 created, 0 updated, 0 deleted", out.getvalue())

    def test_dry_run_reports_drift_and_exits_non_zero(self):
        """--dry-run is usable as a drift alarm, so drift must fail the command."""
        row = FederalPovertyLimitValue.objects.get(period="2026", household_size=4)
        row.annual_limit = 1
        row.save(update_fields=["annual_limit"])
        err = StringIO()

        with self.assertRaises(SystemExit) as raised:
            call_command("sync_fpl_values", "--dry-run", stderr=err)
        row.refresh_from_db()

        self.assertEqual(raised.exception.code, 1)
        self.assertIn("OUT OF DATE", err.getvalue())
        self.assertEqual(row.annual_limit, 1, "dry run must not write")

    def test_dry_run_is_quiet_and_succeeds_when_in_sync(self):
        out = StringIO()

        call_command("sync_fpl_values", "--dry-run", stdout=out)

        self.assertIn("up to date", out.getvalue())

    def test_dry_run_counts_match_a_real_sync(self):
        """The preview and the write share one diff, so they cannot disagree.

        A separate preview implementation would drift from the real one and start
        lying about what a sync would do -- the point of threading dry_run through
        sync_fpl_values rather than recomputing the diff in the command.
        """
        FederalPovertyLimitValue.objects.filter(period="2026", household_size__in=[4, 5]).delete()
        row = FederalPovertyLimitValue.objects.get(period="2025", household_size=1)
        row.annual_limit = 1
        row.save(update_fields=["annual_limit"])
        FederalPovertyLimitValue.objects.create(period="1999", household_size=1, annual_limit=1)

        previewed = sync_fpl_values(dry_run=True)
        actual = sync_fpl_values()

        self.assertEqual(previewed, {"created": 2, "updated": 1, "deleted": 1})
        self.assertEqual(previewed, actual)

    def test_dry_run_writes_nothing(self):
        FederalPovertyLimitValue.objects.filter(period="2026").delete()
        before = FederalPovertyLimitValue.objects.count()

        sync_fpl_values(dry_run=True)

        self.assertEqual(FederalPovertyLimitValue.objects.count(), before)
