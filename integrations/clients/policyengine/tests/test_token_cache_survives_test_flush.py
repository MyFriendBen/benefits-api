"""The PolicyEngine bearer token has to outlive the between-test cache flush.

PolicyEngine issues a limited number of long-life (30-day) tokens per month, and
``_fetch_pe_bearer_token`` only avoids requesting a new one when it finds the last one in the
Django cache. conftest's autouse ``clear_cache`` fixture flushes that cache before every test, so
without an exemption a recording run mints one token per test that reaches the network.
"""

from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from benefits.tests.cache_override import LOCAL_CACHE
from conftest import _preserved_cache_entries
from integrations.clients.policyengine.engines import _PE_TOKEN_CACHE_KEY


# Every test here reads and writes the one global token key. On the ambient Redis
# that key is shared with every other concurrently running test process, which can
# set or clear it mid-test; pin these to a per-process cache so they observe only
# their own writes.
@override_settings(CACHES=LOCAL_CACHE)
class TestPeTokenSurvivesTestCacheFlush(TestCase):
    def test_token_is_carried_across_a_flush(self):
        """The whole point: a token set before the flush is still readable after it."""
        cache.set(_PE_TOKEN_CACHE_KEY, "token-abc", timeout=600)

        preserved = _preserved_cache_entries()
        cache.clear()
        for key, value, timeout in preserved:
            cache.set(key, value, timeout=timeout)

        self.assertEqual(cache.get(_PE_TOKEN_CACHE_KEY), "token-abc")

    def test_nothing_else_is_carried_across_a_flush(self):
        """Only the credential is exempt - ordinary cache state must still be isolated."""
        cache.set(_PE_TOKEN_CACHE_KEY, "token-abc", timeout=600)
        cache.set("some_other_key", "should not survive", timeout=600)

        preserved = _preserved_cache_entries()

        self.assertEqual([key for key, _, _ in preserved], [_PE_TOKEN_CACHE_KEY])

    def test_absent_token_is_not_resurrected(self):
        """With no token cached there is nothing to preserve, and no placeholder is invented."""
        cache.delete(_PE_TOKEN_CACHE_KEY)

        self.assertEqual(_preserved_cache_entries(), [])

    def test_expired_token_is_not_restored(self):
        """A ttl of 0 means the key is gone, even though the read above returned a value.

        django_redis reports 0 for a key that is absent or already expired, which the read can
        race. Restoring on that signal would put a dead token back with no expiry, and every
        caller would use it until something got a 401.
        """
        cache.set(_PE_TOKEN_CACHE_KEY, "token-abc", timeout=600)

        with mock.patch.object(cache, "ttl", return_value=0, create=True):
            self.assertEqual(_preserved_cache_entries(), [])

    def test_token_with_no_expiry_is_restored_with_no_expiry(self):
        """A ttl of None means the key exists and never expires - distinct from a ttl of 0.

        ``seed_pe_token`` stores its placeholder this way, so conflating the two signals would
        either drop it or, worse, treat a genuinely expired token as unexpiring.
        """
        cache.set(_PE_TOKEN_CACHE_KEY, "token-abc", timeout=None)

        with mock.patch.object(cache, "ttl", return_value=None, create=True):
            self.assertEqual(_preserved_cache_entries(), [(_PE_TOKEN_CACHE_KEY, "token-abc", None)])

    def test_remaining_expiry_is_preserved_not_extended(self):
        """Restoring must not hand a stale token a fresh 30-day lease.

        Carrying the remaining TTL keeps the cache entry expiring when the token really does. A
        token that outlives its lease would 401, and ``PrivateApiSim`` evicts the key on 401 and
        requests a new one - self-healing, but only if the entry expires roughly on time.
        """
        cache.set(_PE_TOKEN_CACHE_KEY, "token-abc", timeout=600)

        ((_, _, timeout),) = _preserved_cache_entries()

        if hasattr(cache, "ttl"):
            self.assertIsNotNone(timeout)
            self.assertLessEqual(timeout, 600)
        else:
            self.assertIsNone(timeout)
