"""Tests for the Redis connection-pool wiring.

A missing ssl_cert_reqs took /api/translations/ down on staging for ~3h: Heroku
serves rediss:// with a self-signed cert, redis-py rejected every connection, and
IGNORE_EXCEPTIONS turned that into a silent permanent cache miss. These tests pin
the scheme handling so that cannot regress unnoticed.
"""

from django.test import SimpleTestCase

from benefits.cache_config import DEFAULT_MAX_CONNECTIONS, redis_pool_kwargs

HEROKU_TLS_URL = "rediss://:password@ec2-1-2-3-4.compute-1.amazonaws.com:20740"
LOCAL_URL = "redis://127.0.0.1:6379/1"


class TestRedisPoolKwargs(SimpleTestCase):
    def test_tls_url_disables_cert_verification(self):
        """Heroku's self-signed cert requires ssl_cert_reqs=None."""
        self.assertIsNone(redis_pool_kwargs(HEROKU_TLS_URL)["ssl_cert_reqs"])

    def test_plain_url_omits_ssl_cert_reqs(self):
        """redis-py raises TypeError if a non-TLS connection gets ssl_cert_reqs."""
        self.assertNotIn("ssl_cert_reqs", redis_pool_kwargs(LOCAL_URL))

    def test_pool_stays_under_the_heroku_mini_connection_limit(self):
        """Heroku Redis mini permits 20 connections across all dynos and workers."""
        for url in (HEROKU_TLS_URL, LOCAL_URL):
            with self.subTest(url=url):
                self.assertLess(redis_pool_kwargs(url)["max_connections"], 20)

    def test_retry_on_timeout_enabled(self):
        for url in (HEROKU_TLS_URL, LOCAL_URL):
            with self.subTest(url=url):
                self.assertTrue(redis_pool_kwargs(url)["retry_on_timeout"])

    def test_max_connections_is_overridable(self):
        self.assertEqual(redis_pool_kwargs(LOCAL_URL, max_connections=5)["max_connections"], 5)
        self.assertEqual(redis_pool_kwargs(LOCAL_URL)["max_connections"], DEFAULT_MAX_CONNECTIONS)

    def test_ssl_cert_reqs_is_accepted_by_a_real_tls_pool(self):
        """Guard the kwarg name itself against a redis-py rename.

        Builds the pool but never connects, so no server is needed.
        """
        import redis

        redis.ConnectionPool.from_url(HEROKU_TLS_URL, **redis_pool_kwargs(HEROKU_TLS_URL))

    def test_plain_pool_would_reject_ssl_cert_reqs(self):
        """Documents why the scheme check exists rather than always passing it."""
        import redis

        with self.assertRaises(TypeError):
            redis.ConnectionPool.from_url(LOCAL_URL, ssl_cert_reqs=None).get_connection()
