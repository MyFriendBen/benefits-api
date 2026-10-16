"""Sentry `before_send` hook that keeps street addresses and upstream API keys out of events.

The CESN Calculate Impact page sends an address to two proxies: Places autocomplete
(to Google) and REM impact (to Rewiring America). Our privacy policy says we don't save
addresses, so an event from either endpoint drops everything that could carry one: the
request body and the stack-frame locals (where even the `request` repr includes the URL).

For every event, query strings are dropped from the request and from outgoing-request
(`httplib`) breadcrumbs. Outgoing queries carry upstream keys, e.g. Google's `key=`.
"""

import re
from typing import Any

ADDRESS_ENDPOINT_RE = re.compile(r"/api/(places/autocomplete|screener-options/[^/]+/rem-impact)/?$")


def _strip_query(url: Any) -> Any:
    return url.split("?", 1)[0] if isinstance(url, str) else url


def _drop_frame_vars(event: dict[str, Any]) -> None:
    for exc in (event.get("exception") or {}).get("values") or []:
        for frame in (exc.get("stacktrace") or {}).get("frames") or []:
            frame.pop("vars", None)
    for thread in (event.get("threads") or {}).get("values") or []:
        for frame in (thread.get("stacktrace") or {}).get("frames") or []:
            frame.pop("vars", None)


def scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("query_string", None)
        request["url"] = _strip_query(request.get("url"))
        if ADDRESS_ENDPOINT_RE.search(request.get("url") or ""):
            request.pop("data", None)
            _drop_frame_vars(event)

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
    return event
