"""Request-scoped registry for external-API failures.

When an eligibility run degrades because an external dependency failed (e.g.
PolicyEngine is unreachable, or the fallback path couldn't serve results), we want
that fact to reach the frontend so it can warn the user that results may be
incomplete — rather than silently presenting a partial/altered result set.

Integrations record a failure with `record_external_api_failure(service_id)`; the
results view wraps the eligibility computation in `track_external_api_failures()` and
reads the collected ids with `get_external_api_failures()`.

Most callers should use `report_external_api_failure(...)` instead, which both records
the failure and surfaces it loudly in Sentry — the two things that always want to happen
together when an integration degrades a results run.

The collector is a `contextvars.ContextVar`, so it is isolated per request/thread and
resets cleanly when the context manager exits. `record_...` is a no-op when no context
is active, so deep integration code can call it unconditionally (safe from unit tests,
management commands, or code paths that don't wrap a tracking context).
"""

import contextvars
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from sentry_sdk import capture_exception, capture_message

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


def report_external_api_failure(
    service_id: str,
    message: str,
    exception: Optional[BaseException] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Record an external-API failure AND surface it loudly in Sentry.

    This is the canonical handling for "an integration we depend on failed, so this
    results run is degraded": one Sentry error event for the exception (when there is
    one) plus one for the human-readable context, then the request-scoped record that
    makes `missing_programs` true and populates `external_api_failures` for the
    frontend.

    Reports at most ONCE per service per tracking context. A single screen makes several
    independent calls to the same integration (five HUD lookups across the MA
    calculators, one PolicyEngine call per method), each raising its own exception, so
    without this an outage produces a double-digit event count per screen while telling
    us nothing the first event didn't. Subsequent failures for an already-reported
    service are dropped silently — the flag is already set, and it is a set.

    `message` must be a STATIC string: Sentry groups `capture_message` events by their
    text, so interpolating a screen id or an upstream response body into it creates a
    new issue per screen. Put that detail in `context` instead, which is attached to the
    event as structured data. `fingerprint` is pinned to the service id for the same
    reason.

    Callers that only want the flag (no Sentry noise) can use
    `record_external_api_failure` directly.
    """
    if service_id in get_external_api_failures():
        # Already reported for this run; the record is a set, so nothing left to do.
        return

    contexts = {"external_api": {"service": service_id, **(context or {})}}
    fingerprint = ["external-api-failure", service_id]

    if exception is not None:
        capture_exception(exception, level="error", contexts=contexts, fingerprint=fingerprint)
    capture_message(message, level="error", contexts=contexts, fingerprint=fingerprint)
    record_external_api_failure(service_id)
