"""Sentry `before_send` hook that keeps personal data out of events.

Request bodies are never sent, on any endpoint (MFB-2554). Every DRF error response becomes a
Sentry event (`benefits.views.drf_exception_handler`), and Sentry's Django integration attaches
the request body to it: the name, email and cell from the sign-up endpoint, household details
from the screen endpoints. Two layers keep them out. `SENTRY_PRIVACY_OPTIONS` sets the SDK's
`max_request_body_size` to "never", so the body is not read into the event at all, and
`scrub_event` drops `request.data` from every event as a backstop. Nothing attaches a body
implicitly, so one needed for debugging has to be opted in by the code that raises it, for
example with `sentry_sdk.set_context`, one endpoint at a time.

Four more things are covered: CESN street addresses (with the Google Places API key), the
phone number or email sent to Save My Results (MFB-2437), Celery job arguments, and
Twilio message SIDs (both for the Benji SMS worker, MFB-2436).

The CESN Calculate Impact page sends an address to two proxies: Places autocomplete
(forwarded to Google with our `key`) and REM impact (forwarded to Rewiring America). Our
privacy policy says we don't save addresses, so an event from either endpoint drops
everything that could carry one: the query string, the request body, stack-frame locals
(even the `request` repr includes the URL) and the query on outgoing-request (`httplib`)
breadcrumbs. Events from other endpoints are left alone.

Save My Results: the message endpoint's body is the phone number or email to send the
results to, and the view's locals hold it too. Every error response from it becomes a
Sentry event (`benefits.views.drf_exception_handler`), so a refused number or a failed
send would otherwise put the raw number in Sentry. Those events get the same treatment
as the address endpoints, and their exception messages have anything shaped like a
phone number or an email address replaced: Twilio's error for a rejected number quotes
the number, and a mail provider's can quote the address. Error codes are short enough
to survive.

Celery jobs: Sentry's Celery integration switches itself on once Celery is installed, and
every event raised inside a job carries the job's arguments (`extra["celery-job"]`) and the
stack-frame locals. For a Benji SMS turn those are the inbound Twilio MessageSid, which
resolves to the phone number at Twilio, and, once the turn exists, the number and message
text it reads. Those events keep the task name and id and lose the arguments and locals.
The dead-letter alarm (screener/tasks.py) already logs the ids that matter.

Message SIDs: a Twilio MessageSid resolves to the phone number at Twilio, so it is kept out
of Sentry like the number. Beyond job arguments it can surface anywhere: Celery's "Task ...
received" breadcrumbs, the URL of an outgoing request to Twilio's Messages API, or a Twilio
error's text. Every string in every event that contains one has it replaced. The pattern
(SM or MM, then 32 hex digits) is specific enough that nothing else matches it.

It runs on the serialized event, so nothing it changes is a live object.
"""

import re
from typing import Any

ADDRESS_ENDPOINT_RE = re.compile(r"/api/(places/autocomplete|screener-options/[^/]+/rem-impact)/?$")
CONTACT_ENDPOINT_RE = re.compile(r"/api/messages/?$")
# Nine or more digits, allowing the usual punctuation between them: long enough to
# leave Twilio error codes (five digits) and HTTP statuses alone.
PHONE_LIKE_RE = re.compile(r"\+?\d(?:[\s().-]*\d){8,}")
EMAIL_LIKE_RE = re.compile(r"[^\s@<>\"']+@[^\s@<>\"']+")
REDACTED_CONTACT = "[contact]"

# A Twilio message SID (screener.tasks.MESSAGE_SID_RE), anywhere inside a string.
MESSAGE_SID_RE = re.compile(r"(SM|MM)[0-9a-f]{32}")
REDACTED_SID = "[MessageSid]"


def _redact_message_sids(value: Any) -> Any:
    if isinstance(value, str):
        return MESSAGE_SID_RE.sub(REDACTED_SID, value)
    if isinstance(value, dict):
        return {key: _redact_message_sids(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_message_sids(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_message_sids(item) for item in value)
    return value


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


def _redact_contacts(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return PHONE_LIKE_RE.sub(REDACTED_CONTACT, EMAIL_LIKE_RE.sub(REDACTED_CONTACT, text))


def _redact_contact_messages(event: dict[str, Any]) -> None:
    for value in (event.get("exception") or {}).get("values") or []:
        if "value" in value:
            value["value"] = _redact_contacts(value["value"])
    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        for key in ("message", "formatted"):
            if key in logentry:
                logentry[key] = _redact_contacts(logentry[key])
        logentry.pop("params", None)
    if "message" in event:
        event["message"] = _redact_contacts(event["message"])


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
    event = _redact_message_sids(event)
    if _is_celery_job_event(event):
        _strip_celery_job(event)

    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
    url = _strip_query(request.get("url")) if isinstance(request, dict) else None
    if not url or not (ADDRESS_ENDPOINT_RE.search(url) or CONTACT_ENDPOINT_RE.search(url)):
        return event

    request["url"] = _strip_query(request.get("url"))
    request.pop("query_string", None)
    _drop_frame_vars(event)
    _strip_httplib_queries(event)
    if CONTACT_ENDPOINT_RE.search(url):
        _redact_contact_messages(event)
    return event


# The privacy-relevant `sentry_sdk.init` options, shared by settings and the tests that send
# real events through the SDK so the tests exercise the configuration production runs.
SENTRY_PRIVACY_OPTIONS: dict[str, Any] = {
    "before_send": scrub_event,
    "max_request_body_size": "never",
}
