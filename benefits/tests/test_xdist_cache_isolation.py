"""Per-worker Redis isolation for parallel test runs.

``clear_cache`` empties the cache before every test, and on django_redis ``clear()``
issues FLUSHDB -- the whole database, ignoring KEY_PREFIX. Workers sharing a database
therefore delete each other's entries mid-test, which surfaced in CI as a worker losing
the PolicyEngine bearer token ``seed_pe_token`` had just written and falling through to
a live auth attempt.
"""

import os
import unittest
from unittest import mock

from decouple import config
from django.test import SimpleTestCase, override_settings

from benefits.cache_config import redis_pool_kwargs
from conftest import (
    PE_RECORD_ENV_VAR,
    REDIS_DATABASE_COUNT,
    _isolatable_database_count,
    _isolate_cache_per_xdist_worker,
    _rebuild_cache_connections,
    _redis_database,
    _run_records_cassettes,
    redis_url_for_database,
    vcr_record_mode,
)

# Read the ambient URL like benefits/tests/test_redis_backend.py does, rather than
# hardcoding a host: the connection assertions below open a real socket, so a developer
# whose Redis lives elsewhere (or nowhere) should skip rather than error.
REDIS_URL = config("REDIS_URL", default=None)
BASE_LOCATION = REDIS_URL or "redis://127.0.0.1:6379/0"


def _redis_available() -> bool:
    if not REDIS_URL:
        return False
    try:
        import redis

        kwargs = redis_pool_kwargs(REDIS_URL)
        ssl = {"ssl_cert_reqs": None} if "ssl_cert_reqs" in kwargs else {}
        redis.from_url(REDIS_URL, socket_connect_timeout=2, **ssl).ping()
        return True
    except Exception:
        return False


# These tests only read back the database a connection resolved to; they never store
# anything. Point them at the highest database rather than the one REDIS_URL names: the
# autouse clear_cache fixture FLUSHDBs whatever this class resolves to, and FLUSHDB
# ignores KEY_PREFIX, so targeting the base database would wipe the keys
# benefits/tests/test_redis_backend.py is asserting on from a concurrent worker -- the
# very cross-worker flush this module exists to verify is prevented.
SCRATCH_DATABASE = REDIS_DATABASE_COUNT - 1
SCRATCH_LOCATION = redis_url_for_database(BASE_LOCATION, SCRATCH_DATABASE)

# A fresh dict per test module: _isolate_cache_per_xdist_worker mutates
# settings.CACHES in place, and override_settings does not copy it.
REDIS_CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": SCRATCH_LOCATION}}


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


@unittest.skipUnless(_redis_available(), "REDIS_URL not set or Redis unreachable")
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

        # Back to the scratch database, so the autouse clear_cache flush that follows
        # cannot reach the base database or another worker's.
        settings.CACHES["default"]["LOCATION"] = SCRATCH_LOCATION
        _rebuild_cache_connections()

    def test_the_connection_moves_not_just_the_setting(self):
        """The regression: settings said db N while the connection stayed on the base."""
        expected = _redis_database(BASE_LOCATION) + 1 + 3

        self.assertEqual(self._resolved_database("gw3"), str(expected))

    def test_workers_never_get_the_base_database(self):
        """The base database stays free for serial runs and for test_redis_backend.py,
        which pins REDIS_URL directly and flushes whatever it points at. Offsetting from
        0 rather than from the configured database put gw0 straight onto it."""
        base = str(_redis_database(BASE_LOCATION))
        databases = {self._resolved_database(f"gw{i}") for i in range(_isolatable_database_count())}

        self.assertNotIn(base, databases)

    def test_each_worker_gets_a_distinct_database(self):
        count = _isolatable_database_count()
        databases = [self._resolved_database(f"gw{i}") for i in range(count)]

        self.assertEqual(len(set(databases)), count)

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


class TestOnceIsNotAWritePathUnderParallelism(SimpleTestCase):
    """``once`` is write-protected only after a cassette has been loaded.

    ``Cassette.write_protected`` is ``rewound and record_mode == ONCE``, and ``rewound``
    is set only by a successful ``_load()``. A missing cassette therefore leaves ``once``
    free to record, so two workers reaching the same missing cassette would each call the
    live API and race to write one file. Downgrading to ``none`` in a worker removes the
    write path while keeping the fan-out, which serializing every ``once`` run would not.
    """

    def _effective_mode(self, vcr_mode: str | None, worker: str | None, pe_record: str | None = None) -> str:
        env = {
            "VCR_MODE": vcr_mode or "",
            "PYTEST_XDIST_WORKER": worker or "",
            PE_RECORD_ENV_VAR: pe_record or "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            if not worker:
                os.environ.pop("PYTEST_XDIST_WORKER", None)
            return vcr_record_mode()

    def test_once_becomes_none_in_a_worker(self):
        self.assertEqual(self._effective_mode("once", "gw0"), "none")

    def test_an_unset_mode_becomes_none_in_a_worker(self):
        """The default. Without this, a plain parallel `pytest` can record live."""
        self.assertEqual(self._effective_mode(None, "gw3"), "none")

    def test_once_is_preserved_in_a_serial_run(self):
        """Serial runs keep the stricter-erroring behaviour `once` is chosen for."""
        self.assertEqual(self._effective_mode("once", None), "once")

    def test_an_opted_in_recording_run_keeps_once(self):
        """PE_RECORD=1 VCR_MODE=once is the documented recording command; it is already
        single-process by the time it runs, so there is nothing to protect against."""
        self.assertEqual(self._effective_mode("once", "gw0", pe_record="1"), "once")

    def test_explicit_recording_modes_are_untouched(self):
        self.assertEqual(self._effective_mode("all", "gw0"), "all")
        self.assertEqual(self._effective_mode("new_episodes", "gw0"), "new_episodes")
