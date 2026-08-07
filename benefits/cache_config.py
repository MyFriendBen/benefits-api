"""Cache backend configuration helpers.

Kept in its own module, rather than inline in settings.py, so the Redis wiring
can be unit-tested without importing settings or standing up a TLS server.
"""

# Heroku Redis mini allows 20 connections in total, shared across every dyno and
# worker. Keep the per-process pool well under that.
DEFAULT_MAX_CONNECTIONS = 15


def redis_pool_kwargs(redis_url: str, max_connections: int = DEFAULT_MAX_CONNECTIONS) -> dict:
    """Build CONNECTION_POOL_KWARGS appropriate to the URL's scheme.

    Heroku Redis terminates TLS with a self-signed cert, which redis-py rejects
    by default (ssl_cert_reqs="required") -- every operation then fails with
    CERTIFICATE_VERIFY_FAILED. Combined with IGNORE_EXCEPTIONS that looks exactly
    like a permanent cache miss, so it is easy to ship and hard to spot.

    ssl_cert_reqs is only accepted by TLS connections; passing it to a plain
    redis:// pool raises TypeError at connect time, hence the scheme check.
    """
    kwargs = {
        "max_connections": max_connections,
        "retry_on_timeout": True,
    }
    if redis_url.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = None
    return kwargs
