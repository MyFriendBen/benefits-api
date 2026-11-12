"""Celery broker configuration helpers (MFB-2436).

Kept out of settings.py, like cache_config, so the broker wiring can be unit-tested
without importing settings or standing up a TLS server.

THE BROKER IS NOT THE CACHE. The broker is its own Heroku Redis add-on, attached as
CELERY_BROKER (so its URL arrives as CELERY_BROKER_URL), with `maxmemory-policy
noeviction`. Nothing here ever falls back to REDIS_URL: the cache Redis is 25 MB,
shared with every cache in the app, may evict, and is wrapped in IGNORE_EXCEPTIONS so
an outage reads as a miss. A queue on it would lose jobs silently under memory
pressure. See docs/BENJI_SMS_WORKER.md.
"""

import ssl
from typing import Optional

# Ready messages for one queue live in a Redis list named after the queue. kombu splits
# a queue into one list per priority step and names the others "<queue>\x06\x16<step>"
# (kombu.transport.redis: PRIORITY_STEPS and Channel.sep). Nothing here sets a priority,
# so everything lands in the bare list, but a depth check that reads only that list
# would miss a message someone did enqueue with one.
KOMBU_PRIORITY_STEPS = (0, 3, 6, 9)
KOMBU_PRIORITY_SEP = "\x06\x16"

# Seconds. Applies to the broker client's connect and to every read and write on it.
# Short, because the enqueue happens inside the inbound webhook (MFB-2439), which
# Twilio wants acknowledged quickly; a broker that does not answer in 5 s is down.
BROKER_SOCKET_TIMEOUT = 5

# Connections each process keeps to the broker. Heroku Redis mini allows 20 in total,
# across every web dyno, worker child and one-off dyno, so keep this small.
BROKER_POOL_LIMIT = 4


def broker_use_ssl(broker_url: str) -> Optional[dict]:
    """Celery's broker_use_ssl / redis_backend_use_ssl for this URL.

    Heroku Redis terminates TLS with a self-signed certificate. Celery refuses a
    rediss:// URL without an explicit ssl_cert_reqs (it raises at connect), and
    verification against the system store fails, so the add-on is reached with
    verification off, exactly as the cache is (cache_config.redis_pool_kwargs).
    Plain redis:// (local, CI) takes no SSL options at all.
    """
    if broker_url.startswith("rediss://"):
        return {"ssl_cert_reqs": ssl.CERT_NONE}
    return None


def broker_client_kwargs(broker_url: str) -> dict:
    """Keyword arguments for redis.Redis.from_url when reading the broker directly.

    Only the broker alarm (check_benji_sms_broker) does that; Celery manages its own
    connections. redis-py spells "no verification" as ssl_cert_reqs=None, and accepts
    it only on a TLS URL.
    """
    kwargs: dict = {
        "socket_timeout": BROKER_SOCKET_TIMEOUT,
        "socket_connect_timeout": BROKER_SOCKET_TIMEOUT,
    }
    if broker_url.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = None
    return kwargs


def queue_list_names(queue: str) -> list[str]:
    """Every Redis list kombu may hold ready messages for `queue` in."""
    return [queue] + [f"{queue}{KOMBU_PRIORITY_SEP}{step}" for step in KOMBU_PRIORITY_STEPS if step]
