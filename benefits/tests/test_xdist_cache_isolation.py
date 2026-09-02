"""Per-worker Redis isolation for parallel test runs.

``clear_cache`` empties the cache before every test, and on django_redis ``clear()``
issues FLUSHDB -- the whole database, ignoring KEY_PREFIX. Workers sharing a database
therefore delete each other's entries mid-test, which surfaced in CI as a worker losing
the PolicyEngine bearer token ``seed_pe_token`` had just written and falling through to
a live auth attempt.
"""

import pytest
from django.test import SimpleTestCase, override_settings

from conftest import (
    MAX_ISOLATED_WORKERS,
    _isolate_cache_per_xdist_worker,
    redis_url_for_database,
)

REDIS_CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": "redis://localhost:6379/0"}}


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
    def _location_for(self, worker_id: str) -> str:
        from django.conf import settings

        settings.CACHES["default"]["LOCATION"] = "redis://localhost:6379/0"
        _isolate_cache_per_xdist_worker(worker_id)
        return settings.CACHES["default"]["LOCATION"]

    def test_workers_never_get_database_zero(self):
        """Database 0 stays free for non-xdist runs and for test_redis_backend.py,
        which pins REDIS_URL directly and flushes whatever it points at."""
        databases = {self._location_for(f"gw{i}").rsplit("/", 1)[1] for i in range(MAX_ISOLATED_WORKERS)}

        self.assertNotIn("0", databases)

    def test_each_worker_gets_a_distinct_database(self):
        databases = [self._location_for(f"gw{i}") for i in range(MAX_ISOLATED_WORKERS)]

        self.assertEqual(len(set(databases)), MAX_ISOLATED_WORKERS)

    def test_a_worker_beyond_the_database_count_is_an_error(self):
        """Wrapping with % would put this worker back on database 0, where it would
        flush the entries of whatever else is using it -- the bug this guards."""
        with self.assertRaises(pytest.UsageError):
            self._location_for(f"gw{MAX_ISOLATED_WORKERS}")

    def test_a_non_redis_cache_is_left_alone(self):
        from django.conf import settings

        with override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}):
            _isolate_cache_per_xdist_worker("gw0")

            self.assertNotIn("LOCATION", settings.CACHES["default"])
