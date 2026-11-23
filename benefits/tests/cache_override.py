"""Shared cache override for tests that assert on real cache reads and writes.

The suite must not depend on whether the ambient REDIS_URL happens to point at a
reachable server. With IGNORE_EXCEPTIONS a down Redis turns every set into a silent
no-op, so such tests fail confusingly on a developer machine while passing in CI.

Apply as a class decorator -- `override_settings` is the mechanism that works with
django.test.TestCase, which pytest-django's `settings` fixture does not:

    from django.test import override_settings
    from benefits.tests.cache_override import LOCAL_CACHE

    @override_settings(CACHES=LOCAL_CACHE)
    class TestSomething(TestCase):
        ...

Tests that deliberately exercise the django_redis backend belong in
benefits/tests/test_redis_backend.py instead.
"""

LOCAL_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}
