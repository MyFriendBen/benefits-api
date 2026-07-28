"""Tests for GoogleSheetsCache.get_data() — the shared fetch/cache/fallback logic
used by roughly 10 program-specific Sheets-backed caches (BoulderAmiCache,
CccapFplCache, RAGCache, ACACache, NcHeadStartMarketRatesCache,
CoHeadStartCountyEligibleCache, LeapValueCache, CfhCountyValuesCache, Ami, Smi,
IncomeLimitsCache). Exercised here directly against a minimal fake subclass
rather than through any one of the real callers, since the logic under test
(caching, stale fallback, error handling) is identical across all of them."""

from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from integrations.services.sheets.cache import GoogleSheetsCache


class FakeSheetsCache(GoogleSheetsCache):
    """Minimal concrete subclass for exercising GoogleSheetsCache in isolation.

    `process_result` is returned by `_process`; set `raise_error` to an exception
    instance instead to simulate a fetch/process failure. `fetch_raw_calls` and
    `process_calls` let tests assert whether a re-fetch actually happened.
    """

    CACHE_KEY = "test_fake_sheets_cache"

    def __init__(self, process_result=None, raise_error=None):
        self.process_result = process_result
        self.raise_error = raise_error
        self.fetch_raw_calls = 0
        self.process_calls = 0

    def _fetch_raw(self):
        self.fetch_raw_calls += 1
        return "raw"

    def _process(self, raw_data):
        self.process_calls += 1
        if self.raise_error is not None:
            raise self.raise_error
        return self.process_result


class TestGoogleSheetsCacheGetData(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_successful_fetch_returns_and_caches_data(self):
        fake = FakeSheetsCache(process_result={"county": "value"})

        result = fake.get_data()

        self.assertEqual(result, {"county": "value"})
        # Both keys must be populated - the stale key is what lets a later
        # failure serve this value instead of an empty fallback.
        self.assertEqual(cache.get(fake.CACHE_KEY), {"county": "value"})
        self.assertEqual(cache.get(fake._stale_cache_key), {"county": "value"})

    def test_cache_hit_does_not_refetch(self):
        fake = FakeSheetsCache(process_result={"county": "value"})
        fake.get_data()  # prime the cache

        result = fake.get_data()

        self.assertEqual(result, {"county": "value"})
        self.assertEqual(fake.fetch_raw_calls, 1)
        self.assertEqual(fake.process_calls, 1)

    def test_empty_result_without_stale_data_returns_empty_fallback(self):
        fake = FakeSheetsCache(process_result={})

        result = fake.get_data()

        self.assertEqual(result, {})
        # An empty result must not be cached, so the next call retries instead
        # of being stuck serving nothing for the full CACHE_TIMEOUT.
        self.assertIsNone(cache.get(fake.CACHE_KEY))

    def test_empty_result_with_stale_data_serves_stale_data(self):
        good = FakeSheetsCache(process_result={"county": "value"})
        good.get_data()  # populate the stale cache with a real value
        # Clear only the primary key, simulating its shorter TTL expiring while
        # the longer-lived stale key is still valid - otherwise get_data()'s
        # cache-hit check would short-circuit before ever calling _process().
        cache.delete(good.CACHE_KEY)

        empty = FakeSheetsCache(process_result={})
        result = empty.get_data()

        self.assertEqual(result, {"county": "value"})

    @patch("integrations.services.sheets.cache.capture_exception")
    def test_exception_without_stale_data_reports_and_returns_empty_fallback(self, mock_capture):
        fake = FakeSheetsCache(raise_error=RuntimeError("sheets is down"))

        result = fake.get_data()

        self.assertEqual(result, {})
        mock_capture.assert_called_once()
        self.assertIsNone(cache.get(fake.CACHE_KEY))

    @patch("integrations.services.sheets.cache.capture_exception")
    def test_exception_with_stale_data_reports_and_serves_stale_data(self, mock_capture):
        good = FakeSheetsCache(process_result={"county": "value"})
        good.get_data()
        # See test_empty_result_with_stale_data_serves_stale_data for why this
        # is needed: without it, the cache-hit check short-circuits before
        # _process() (and therefore the exception) is ever reached.
        cache.delete(good.CACHE_KEY)

        failing = FakeSheetsCache(raise_error=RuntimeError("sheets is down"))
        result = failing.get_data()

        self.assertEqual(result, {"county": "value"})
        mock_capture.assert_called_once()
