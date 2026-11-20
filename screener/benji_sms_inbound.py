"""The Benji SMS inbound webhook: where Twilio posts each text sent to our number (MFB-2439).

Design: MFB-1916 proposal v3, decisions 3, 4, 5, 7 and 10. Runbook: docs/BENJI_SMS_INBOUND.md.

This module is the HTTP edge: Twilio's signature, the form fields, and the status code
Twilio sees. What a text gets is decided in
`integrations.services.communications.benji_sms_inbound.handle_inbound`.

Every text is answered with 200 and empty TwiML; replies go out through the REST API so
each has a delivery row. A request Twilio did not sign is a 403 before anything is read
from the database. A text that could not be fully handled (a turn or a media deletion
that could not be queued) is a 503, so Twilio posts it again, and a replay is safe.

NOTHING HERE LOGS THE NUMBER, ITS HASH OR THE TEXT. Log lines carry the outcome and
Twilio's error code. Sentry events from these URLs lose the request body and stack
locals (benefits/sentry_scrub.py).
"""

import logging
from typing import Any

from django.http import HttpResponse
from sentry_sdk import capture_exception
from rest_framework import parsers, views
from rest_framework.request import Request

from integrations.services.communications.benji_sms_inbound import (
    Inbound,
    MediaDeletionNotQueued,
    Result,
    handle_inbound,
)
from integrations.services.communications.twilio_signature import SignedByTwilio

from .tasks import MESSAGE_SID_RE

logger = logging.getLogger(__name__)

EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
TWIML_CONTENT_TYPE = "text/xml"


def _int_or_zero(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _twiml(status: int = 200) -> HttpResponse:
    return HttpResponse(EMPTY_TWIML, content_type=TWIML_CONTENT_TYPE, status=status)


class BenjiSmsInboundView(views.APIView):
    """`POST /api/assistant/sms/inbound/`, and `.../inbound/fallback/` with `fallback=True`.

    Twilio's signature is the only credential (SignedByTwilio), checked before anything
    is read from the database.

    The fallback URL is where Twilio posts a text after the primary URL failed. It runs
    the same handling, which is safe because a replay changes nothing new, and logs
    Twilio's error code for the alarm in MFB-2441.
    """

    authentication_classes: list = []
    permission_classes = [SignedByTwilio]
    parser_classes = [parsers.FormParser]
    throttle_classes: list = []

    fallback = False

    def post(self, request: Request) -> HttpResponse:
        data = request.data
        sid = str(data.get("MessageSid") or data.get("SmsSid") or "")
        if not MESSAGE_SID_RE.match(sid):
            # Signed by Twilio but not an inbound message. Nothing a retry would fix.
            logger.error("Benji SMS inbound webhook: signed request without a MessageSid.")
            return _twiml(400)

        if self.fallback:
            logger.warning(
                "Benji SMS inbound arrived through the fallback URL: twilio_error=%s",
                _int_or_zero(data.get("ErrorCode")),
            )

        inbound = Inbound(
            sid=sid,
            sender=str(data.get("From") or ""),
            body=str(data.get("Body") or ""),
            num_media=_int_or_zero(data.get("NumMedia")),
            opt_out_type=data.get("OptOutType") or None,
        )
        try:
            result = handle_inbound(inbound)
        except MediaDeletionNotQueued as exc:
            # The text was handled; only its media deletion is outstanding. Log what was
            # decided, since the replay will find it done and report nothing.
            _log_outcome(exc.result)
            logger.error("Benji SMS inbound webhook failed: media deletion not queued (%s)", exc.cause)
            return _twiml(503)
        except Exception as exc:
            # The log line names the class only: an exception's text can quote a key.
            # Sentry gets the traceback, without this view's locals (the number and the
            # message) or anything shaped like a number or SID (benefits/sentry_scrub.py).
            # 503 has Twilio post it again.
            logger.error("Benji SMS inbound webhook failed: %s", f"{type(exc).__module__}.{type(exc).__qualname__}")
            capture_exception(exc)
            return _twiml(503)

        _log_outcome(result)
        return _twiml()


def _log_outcome(result: Result) -> None:
    # The one trace of a decision that sends nothing (revoked, channel off, a second text
    # that day). INFO: this logger has its own handler (settings.LOGGING).
    logger.info("Benji SMS inbound: outcome=%s replied=%s", result.outcome.value, result.replied)
