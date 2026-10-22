"""Sentry `before_send` hook that keeps CESN street addresses and the Google Places API key out of events.

The CESN Calculate Impact page sends an address to two proxies: Places autocomplete
(forwarded to Google with our `key`) and REM impact (forwarded to Rewiring America). Our
privacy policy says we don't save addresses, so an event from either endpoint drops
everything that could carry one: the query string, the request body, stack-frame locals
(even the `request` repr includes the URL) and the query on outgoing-request (`httplib`)
breadcrumbs. Events from other endpoints are left alone.

It runs on the serialized event, so nothing it changes is a live object.
"""

import re
from typing import Any

ADDRESS_ENDPOINT_RE = re.compile(r"/api/(places/autocomplete|screener-options/[^/]+/rem-impact)/?$")


def _strip_query(url: Any) -> Any:
    return url.split("?", 1)[0] if isinstance(url, str) else url


def _drop_frame_vars(event: dict[str, Any]) -> None:
    for key in ("exception", "threads"):
        for value in (event.get(key) or {}).get("values") or []:
            for frame in (value.get("stacktrace") or {}).get("frames") or []:
                frame.pop("vars", None)


def _strip_httplib_queries(event: dict[str, Any]) -> None:
    breadcrumbs = event.get("breadcrumbs")
    crumbs = breadcrumbs.get("values") if isinstance(breadcrumbs, dict) else breadcrumbs
    for crumb in crumbs or []:
        if crumb.get("category") != "httplib":
            continue
        data = crumb.get("data") or {}
        data.pop("http.query", None)
        data.pop("http.fragment", None)
        if "url" in data:
            data["url"] = _strip_query(data["url"])


def scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    request = event.get("request")
    if not isinstance(request, dict) or not ADDRESS_ENDPOINT_RE.search(_strip_query(request.get("url")) or ""):
        return event

    request["url"] = _strip_query(request.get("url"))
    request.pop("query_string", None)
    request.pop("data", None)
    _drop_frame_vars(event)
    _strip_httplib_queries(event)
    return event
