"""Sentry `before_send` hook that keeps CESN street addresses and the Google Places API key out of events.

The CESN Calculate Impact page sends an address to two proxies: Places autocomplete
(`input`, forwarded to Google with our `key`) and REM impact (`address`, forwarded to
Rewiring America). Our privacy policy says we don't save addresses.

The hook filters those params by name: as dict keys (request body, breadcrumb data,
stack-frame locals) and inside strings that carry a query (request URL, outgoing-request
breadcrumbs, and the `request` repr in frame locals). It runs on the serialized event, so
nothing it changes is a live object.
"""

import re
from typing import Any

FILTERED = "[Filtered]"

# Request params, plus the local variable that holds the typed text in the view and client.
SENSITIVE_KEYS = frozenset({"input", "input_text", "address", "key"})

SENSITIVE_QUERY_PARAM_RE = re.compile(r"(^|[?&])(input|address|key)=[^&#\s'\"]*")


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: FILTERED if k in SENSITIVE_KEYS else _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, str):
        return SENSITIVE_QUERY_PARAM_RE.sub(rf"\1\2={FILTERED}", value)
    return value


def scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    for key in ("request", "breadcrumbs", "exception", "threads", "extra"):
        if key in event:
            event[key] = _scrub(event[key])
    return event
