"""Request-scoped registry for external-API failures.

When an eligibility run degrades because an external dependency failed (e.g.
PolicyEngine is unreachable, or the fallback path couldn't serve results), we want
that fact to reach the frontend so it can warn the user that results may be
incomplete — rather than silently presenting a partial/altered result set.

Integrations record a failure with `record_external_api_failure(service_id)`; the
results view wraps the eligibility computation in `track_external_api_failures()` and
reads the collected ids with `get_external_api_failures()`.

The collector is a `contextvars.ContextVar`, so it is isolated per request/thread and
resets cleanly when the context manager exits. `record_...` is a no-op when no context
is active, so deep integration code can call it unconditionally (safe from unit tests,
management commands, or code paths that don't wrap a tracking context).
"""

import contextvars
from contextlib import contextmanager
from typing import List

# Stable service identifiers sent to the frontend. Extend as more integrations opt in.
POLICY_ENGINE = "policy_engine"
HUD = "hud"

# None (the default) means "no tracking context is active" — record_...() is a no-op.
_failures: contextvars.ContextVar = contextvars.ContextVar("external_api_failures", default=None)


@contextmanager
def track_external_api_failures():
    """Collect external-API failures for the duration of the block. Read the collected
    ids with get_external_api_failures() inside the block (before it exits).

    Only the outermost context initializes and resets the collector; a nested context
    reuses the existing set so failures recorded inside it stay visible to the outer
    scope (the whole point is "did anything fail during this request")."""
    if _failures.get() is not None:
        # Already tracking (nested): reuse the outer set; the outermost context owns
        # init/reset.
        yield
        return
    token = _failures.set(set())
    try:
        yield
    finally:
        _failures.reset(token)


def record_external_api_failure(service_id: str) -> None:
    """Record that an external dependency failed during the current run. No-op when no
    tracking context is active."""
    failures = _failures.get()
    if failures is not None:
        failures.add(service_id)


def get_external_api_failures() -> List[str]:
    """Sorted list of service ids recorded in the current tracking context (empty if
    none / no active context)."""
    failures = _failures.get()
    return sorted(failures) if failures else []
