"""Sentry `before_send` hook that keeps personal data out of events.

Two sources are covered: CESN street addresses (with the Google Places API key), and
Celery job arguments (the Benji SMS worker, MFB-2436).

The CESN Calculate Impact page sends an address to two proxies: Places autocomplete
(forwarded to Google with our `key`) and REM impact (forwarded to Rewiring America). Our
privacy policy says we don't save addresses, so an event from either endpoint drops
everything that could carry one: the query string, the request body, stack-frame locals
(even the `request` repr includes the URL) and the query on outgoing-request (`httplib`)
breadcrumbs. Events from other endpoints are left alone.

Celery jobs: Sentry's Celery integration switches itself on once Celery is installed, and
every event raised inside a job carries the job's arguments (`extra["celery-job"]`) and the
stack-frame locals. For a Benji SMS turn those are the inbound Twilio MessageSid, which
resolves to the phone number at Twilio, and, once the turn exists, the number and message
text it reads. Those events keep the task name and id and lose the arguments and locals.
The dead-letter alarm (screener/tasks.py) already logs the ids that matter.

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


def _is_celery_job_event(event: dict[str, Any]) -> bool:
    tags = event.get("tags")
    if isinstance(tags, dict) and "celery_task_id" in tags:
        return True
    # The protocol also allows tags as a list of [key, value] pairs.
    if isinstance(tags, list) and any(
        isinstance(tag, (list, tuple)) and tag and tag[0] == "celery_task_id" for tag in tags
    ):
        return True
    extra = event.get("extra")
    return isinstance(extra, dict) and "celery-job" in extra


def _strip_celery_job(event: dict[str, Any]) -> None:
    job = (event.get("extra") or {}).get("celery-job")
    if isinstance(job, dict):
        job.pop("args", None)
        job.pop("kwargs", None)
    _drop_frame_vars(event)


def scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    if _is_celery_job_event(event):
        _strip_celery_job(event)

    request = event.get("request")
    if not isinstance(request, dict) or not ADDRESS_ENDPOINT_RE.search(_strip_query(request.get("url")) or ""):
        return event

    request["url"] = _strip_query(request.get("url"))
    request.pop("query_string", None)
    request.pop("data", None)
    _drop_frame_vars(event)
    _strip_httplib_queries(event)
    return event
