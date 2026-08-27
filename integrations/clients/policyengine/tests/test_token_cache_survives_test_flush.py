"""The PolicyEngine bearer token has to outlive the between-test cache flush.

PolicyEngine issues a limited number of long-life (30-day) tokens per month, and
``_fetch_pe_bearer_token`` only avoids requesting a new one when it finds the last one in the
Django cache. conftest's autouse ``clear_cache`` fixture flushes that cache before every test, so
without an exemption a recording run mints one token per test that reaches the network.
"""

from django.core.cache import cache
from django.test import TestCase

from conftest import _preserved_cache_entries
from integrations.clients.policyengine.engines import _PE_TOKEN_CACHE_KEY


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

    def test_remaining_expiry_is_preserved_not_extended(self):
        """Restoring must not hand a stale token a fresh 30-day lease.

        Carrying the remaining TTL keeps the cache entry expiring when the token really does. A
        token that outlives its lease would 401, and ``PrivateApiSim`` evicts the key on 401 and
        requests a new one - self-healing, but only if the entry expires roughly on time.
        """
        cache.set(_PE_TOKEN_CACHE_KEY, "token-abc", timeout=600)

        (_, _, timeout), = _preserved_cache_entries()

        if hasattr(cache, "ttl"):
            self.assertIsNotNone(timeout)
            self.assertLessEqual(timeout, 600)
        else:
            self.assertIsNone(timeout)
