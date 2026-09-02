"""Per-worker Redis isolation for parallel test runs.

``clear_cache`` empties the cache before every test, and on django_redis ``clear()``
issues FLUSHDB -- the whole database, ignoring KEY_PREFIX. Workers sharing a database
therefore delete each other's entries mid-test, which surfaced in CI as a worker losing
the PolicyEngine bearer token ``seed_pe_token`` had just written and falling through to
a live auth attempt.
"""

import os
from unittest import mock

from django.test import SimpleTestCase, override_settings

from conftest import (
    MAX_ISOLATED_WORKERS,
    PE_RECORD_ENV_VAR,
    _run_records_cassettes,
    _isolate_cache_per_xdist_worker,
    _rebuild_cache_connections,
    redis_url_for_database,
    vcr_record_mode,
)

BASE_LOCATION = "redis://localhost:6379/0"
# A fresh dict per test module: _isolate_cache_per_xdist_worker mutates
# settings.CACHES in place, and override_settings does not copy it.
REDIS_CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": BASE_LOCATION}}


class TestRedisUrlForDatabase(SimpleTestCase):
    def test_replaces_a_plain_database_index(self):
        self.assertEqual(redis_url_for_database("redis://localhost:6379/0", 3), "redis://localhost:6379/3")

    def test_preserves_a_query_string(self):
        """Heroku hands us rediss://...?ssl_cert_reqs=none; see benefits/cache_config.py.

        Splitting on the last "/" would append the database to the query string and
        produce a URL that still parses as a string but cannot connect.
        """
        self.assertEqual(
            redis_url_for_database("rediss://h:6379/0?ssl_cert_reqs=none", 2),
            "rediss://h:6379/2?ssl_cert_reqs=none",
        )

    def test_adds_a_database_to_a_url_that_omits_one(self):
        self.assertEqual(
            redis_url_for_database("redis://h:6379?ssl_cert_reqs=none", 1),
            "redis://h:6379/1?ssl_cert_reqs=none",
        )

    def test_preserves_credentials(self):
        self.assertEqual(redis_url_for_database("redis://user:pw@h:6380/7", 4), "redis://user:pw@h:6380/4")


@override_settings(CACHES=REDIS_CACHES)
class TestWorkerIsolation(SimpleTestCase):
    """Assertions here read the *resolved connection*, not settings.

    Asserting on settings alone passes even when isolation does nothing: the connection
    handler caches connection objects, and the default connection already exists before
    pytest_configure runs (django-parler reads cache.default_timeout at import, so
    django.setup() builds it). Rewriting settings without rebuilding the connection
    leaves every worker flushing database 0 while settings claim otherwise.
    """

    def _resolved_database(self, worker_id: str) -> str:
        from django.conf import settings
        from django.core.cache import cache

        settings.CACHES["default"]["LOCATION"] = BASE_LOCATION
        _isolate_cache_per_xdist_worker(worker_id)
        # cache is a proxy; touching .client resolves the real connection.
        return cache.client._server[0].rsplit("/", 1)[1]

    def tearDown(self):
        from django.conf import settings

        settings.CACHES["default"]["LOCATION"] = BASE_LOCATION
        _rebuild_cache_connections()

    def test_the_connection_moves_not_just_the_setting(self):
        """The regression: settings said db N while the connection stayed on db 0."""
        self.assertEqual(self._resolved_database("gw3"), "4")

    def test_workers_never_get_database_zero(self):
        """Database 0 stays free for non-xdist runs and for test_redis_backend.py,
        which pins REDIS_URL directly and flushes whatever it points at."""
        databases = {self._resolved_database(f"gw{i}") for i in range(MAX_ISOLATED_WORKERS)}

        self.assertNotIn("0", databases)

    def test_each_worker_gets_a_distinct_database(self):
        databases = [self._resolved_database(f"gw{i}") for i in range(MAX_ISOLATED_WORKERS)]

        self.assertEqual(len(set(databases)), MAX_ISOLATED_WORKERS)

    def test_a_non_redis_cache_is_left_alone(self):
        from django.conf import settings

        with override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}):
            _isolate_cache_per_xdist_worker("gw0")

            self.assertNotIn("LOCATION", settings.CACHES["default"])


class TestRecordingModesRunSerially(SimpleTestCase):
    """Which runs may write cassettes, and so must not fan out across workers.

    Two workers recording the same cassette race to write one file, and each issues its
    own live API call. Only modes that actually record belong here: "once" is the default
    when VCR_MODE is unset and writes only when a whole cassette file is absent, so
    treating it as recording silently made every default local run serial.
    """

    def _records(self, vcr_mode: str | None, pe_record: str | None = None) -> bool:
        env = {"VCR_MODE": vcr_mode or "", PE_RECORD_ENV_VAR: pe_record or ""}
        with mock.patch.dict(os.environ, env, clear=False):
            return _run_records_cassettes(vcr_record_mode())

    def test_replay_modes_stay_parallel(self):
        self.assertFalse(self._records("none"))
        self.assertFalse(self._records("once"))

    def test_an_unset_mode_stays_parallel(self):
        """The default. pytest.ini configures -n auto for exactly this case."""
        self.assertFalse(self._records(None))

    def test_recording_modes_go_serial(self):
        self.assertTrue(self._records("all"))
        self.assertTrue(self._records("new_episodes"))

    def test_pe_record_makes_an_otherwise_replaying_run_serial(self):
        """docs/TESTING.md records PolicyEngine cassettes with PE_RECORD=1 VCR_MODE=once,
        which writes cassettes even though the mode alone would not."""
        self.assertTrue(self._records("once", pe_record="1"))
