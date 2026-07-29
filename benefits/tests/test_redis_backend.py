"""Tests that run against a real Redis rather than LocMemCache.

Every other cache test pins LocMemCache for determinism (see benefits.tests.cache_override),
which means nothing would exercise django_redis itself: pickling, zlib compression,
key prefixing, or the connection pool. That gap is how a Redis misconfiguration
reached staging with a green build.

Skipped when REDIS_URL is unset or unreachable, so local runs stay green; CI
provides a redis service container, so there it always runs.
"""

import unittest

from django.core.cache import caches
from django.test import SimpleTestCase, override_settings

from benefits.cache_config import redis_pool_kwargs
from decouple import config

REDIS_URL = config("REDIS_URL", default=None)


def _redis_available() -> bool:
    if not REDIS_URL:
        return False
    try:
        import redis

        client = redis.from_url(REDIS_URL, socket_connect_timeout=2, **_ssl_kwargs())
        client.ping()
        return True
    except Exception:
        return False


def _ssl_kwargs() -> dict:
    kwargs = redis_pool_kwargs(REDIS_URL or "")
    # from_url takes the ssl kwarg directly; max_connections/retry are pool-level.
    return {"ssl_cert_reqs": None} if "ssl_cert_reqs" in kwargs else {}


REDIS_CACHE = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL or "redis://127.0.0.1:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": redis_pool_kwargs(REDIS_URL or ""),
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            # Deliberately NOT ignoring exceptions: these tests exist to surface
            # backend errors rather than silently degrade to a cache miss.
            "IGNORE_EXCEPTIONS": False,
        },
        "KEY_PREFIX": "benefits-test",
        "TIMEOUT": 300,
    }
}


@unittest.skipUnless(_redis_available(), "REDIS_URL not set or Redis unreachable")
@override_settings(CACHES=REDIS_CACHE)
class TestRedisBackend(SimpleTestCase):
    def setUp(self):
        self.cache = caches["default"]
        self.cache.clear()

    def test_set_reports_success(self):
        """A silent None here is what a rejected TLS cert looked like on staging."""
        self.assertIs(self.cache.set("probe", "value", 60), True)

    def test_round_trips_a_string(self):
        self.cache.set("probe", "value", 60)
        self.assertEqual(self.cache.get("probe"), "value")

    def test_round_trips_a_nested_dict(self):
        """Mirrors the translation payload shape: {lang: {label: text}}."""
        payload = {"en-us": {"greeting": "Hello"}, "es": {"greeting": "Hola"}}

        self.cache.set("translations", payload, 60)

        self.assertEqual(self.cache.get("translations"), payload)

    def test_round_trips_a_payload_large_enough_to_compress(self):
        """Translation payloads are ~1MB per language and compress ~3.5x."""
        payload = {f"label_{i}": f"Some translated sentence number {i}." for i in range(20_000)}

        self.cache.set("bulk", payload, 60)

        self.assertEqual(self.cache.get("bulk"), payload)

    def test_get_many_and_set_many(self):
        """The translation cache reads and writes one key per language in bulk."""
        self.cache.set_many({"a": 1, "b": 2}, 60)

        self.assertEqual(self.cache.get_many(["a", "b", "missing"]), {"a": 1, "b": 2})

    def test_delete_many(self):
        self.cache.set_many({"a": 1, "b": 2}, 60)

        self.cache.delete_many(["a", "b"])

        self.assertEqual(self.cache.get_many(["a", "b"]), {})

    def test_missing_key_returns_none(self):
        self.assertIsNone(self.cache.get("never-written"))

    def test_compression_is_actually_applied(self):
        """Guards the COMPRESSOR option against being dropped from settings."""
        highly_compressible = {"k": "a" * 200_000}
        self.cache.set("compressible", highly_compressible, 60)

        raw = self.cache.client.get_client(write=False).get("benefits-test:1:compressible")

        self.assertLess(len(raw), 100_000)
        self.assertEqual(self.cache.get("compressible"), highly_compressible)
