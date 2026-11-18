"""The Benji SMS inbound webhook: where Twilio posts each text sent to our number (MFB-2439).

Design: MFB-1916 proposal v3, decisions 3, 4, 5, 7 and 10. Runbook: docs/BENJI_SMS_INBOUND.md.

The webhook acknowledges fast, decides what state the sending number is in, and either
answers with a fixed reply or queues a turn for the worker. It never calls the model.

WHAT HAPPENS TO A TEXT. In order, first match wins:

 0. Not signed by Twilio             403, before any lookup (SignedByTwilio)
 1. Has media (any state)            queue its deletion at Twilio; then carry on below
 2. Sender is not a phone number     nothing (a short code or an alphanumeric sender)
 3. Unknown number, a keyword        nothing: Twilio answered, and there is no row to change
 4. Unknown number                   the stranger reply, once a day
 5. STOP                             revoke the number, close its conversation
 6. Revoked, START                   clear the revocation, resume the conversation if it can
 7. Revoked, anything else           nothing
 8. HELP                             the HELP reply
 9. START, not revoked               nothing ("yes" is an ordinary answer and carries on)
10. Marked shared                    the shared-phone reply, once a day
11. Quiet past the interval          expire the conversation, then as 12
12. No active conversation           the re-entry reply, once a day
13. Channel off for the white label  nothing
14. Has media                        the "can't read pictures" reply
15. Otherwise                        queue the turn

STOP comes before every other state on purpose: a shared or expired number that texts
STOP must still be revoked.

WHO ANSWERS A KEYWORD. Twilio answers its own keywords itself and blocks our sends after
a STOP, so for those we only change state. Our fixed STOP, HELP and START replies go out
for the wordings Twilio does not handle (benji_sms_keywords.py).

A REPLAYED WEBHOOK SENDS NOTHING NEW. Twilio posts a text again when it does not get our
answer in time, and through the fallback URL after that. Every fixed reply first inserts
its delivery row, which the database allows once per inbound MessageSid
(`BenjiSmsDelivery.objects.claim_fixed`), and the state changes are all safe to repeat.
A replayed turn is queued again and absorbed by the worker, which sends the SID to
ai-service as `client_message_id` (MFB-2440). One gap is accepted: a revoked number's
"yes" clears the revocation, so a replay of that one text finds the number no longer
revoked and queues "yes" as a turn.

SENDS ARE BEST EFFORT, THE QUEUE IS NOT. A fixed reply Twilio refuses is logged and
dropped: the webhook still answers 200, because the state change is what matters and a
retry would not send it either. A turn or a media deletion that cannot be queued answers
503, so Twilio posts the text again.

NOTHING HERE LOGS THE NUMBER, ITS HASH OR THE TEXT. Log lines carry the outcome and
Twilio's error code. Sentry events from these URLs lose the request body and stack
locals (benefits/sentry_scrub.py).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import parsers, views
from rest_framework.request import Request

from integrations.services.communications import benji_sms_replies as replies
from integrations.services.communications.benji_sms import (
    BenjiSmsDeliveryUnknown,
    BenjiSmsSendError,
    can_send_fixed_reply,
    channel_enabled,
    send_fixed_reply,
    send_screen_sms,
)
from integrations.services.communications.benji_sms_hash import InvalidPhoneNumber, phone_hash
from integrations.services.communications.benji_sms_keywords import Keyword, classify
from integrations.services.communications.twilio_signature import SignedByTwilio

from .models import (
    AssistantConversationStatus,
    BenjiSmsBinding,
    BenjiSmsDelivery,
    BenjiSmsPhone,
    BenjiSmsStrangerReply,
)
from .tasks import MESSAGE_SID_RE, enqueue_media_deletion, enqueue_turn

logger = logging.getLogger(__name__)

EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
TWIML_CONTENT_TYPE = "text/xml"

# Twilio's error for a send to a number that opted out with a carrier keyword. Expected
# whenever our keyword list and Twilio's disagree about a wording, so not an alarm.
TWILIO_OPTED_OUT = 21610


class Outcome(str, Enum):
    """What the webhook decided. Logged, and what the tests read."""

    NOT_A_PHONE = "not_a_phone"
    STRANGER_KEYWORD = "stranger_keyword"
    STRANGER = "stranger"
    STOPPED = "stopped"
    STARTED = "started"
    REVOKED = "revoked"
    HELP = "help"
    START_IGNORED = "start_ignored"
    SHARED = "shared"
    REENTRY = "reentry"
    CHANNEL_OFF = "channel_off"
    PICTURE = "picture"
    EMPTY = "empty"
    QUEUED = "queued"


@dataclass(frozen=True)
class Inbound:
    """One inbound text, as Twilio posted it. Lives for the request only."""

    sid: str
    sender: str
    body: str
    num_media: int
    opt_out_type: Optional[str] = None


@dataclass(frozen=True)
class Result:
    outcome: Outcome
    # Whether a fixed reply went to Twilio for this request.
    replied: bool = False


def _locale(binding: Optional[BenjiSmsBinding]) -> Optional[str]:
    return binding.conversation.locale if binding is not None else None


def _send_fixed(
    inbound: Inbound,
    reply: replies.FixedReply,
    binding: Optional[BenjiSmsBinding],
    now: datetime,
    *,
    for_screen: bool,
) -> bool:
    """Send one fixed reply to the sender, at most once per inbound. True if it went.

    `for_screen` replies belong to a conversation and are held to its white label's
    flag; the others (stranger, shared, re-entry) answer a number that has none.
    """
    delivery = BenjiSmsDelivery.objects.claim_fixed(inbound.sid, binding)
    if delivery is None:
        return False

    body = replies.reply_text(reply, _locale(binding))
    try:
        if for_screen and binding is not None:
            outbound_sid = send_screen_sms(inbound.sender, body, white_label=binding.white_label)
        else:
            outbound_sid = send_fixed_reply(inbound.sender, body)
    except BenjiSmsSendError as exc:
        delivery.delete()
        log = logger.warning if exc.code == TWILIO_OPTED_OUT else logger.error
        log("Benji SMS fixed reply not sent: reply=%s status=%s code=%s", reply.label, exc.status, exc.code)
        return False
    except BenjiSmsDeliveryUnknown as exc:
        # It may have gone out. The row stays, with no outbound SID, so a replay does
        # not send a second one.
        logger.error("Benji SMS fixed reply delivery unknown: reply=%s cause=%s", reply.label, exc.cause)
        return False

    if outbound_sid is None:
        # Refused by a gate (kill switch, flag, DEBUG), which logged why.
        delivery.delete()
        return False

    delivery.outbound_sid = outbound_sid
    delivery.sent_at = now
    delivery.save(update_fields=["outbound_sid", "sent_at"])
    return True


def _send_daily(
    inbound: Inbound,
    number_hash: str,
    reply: replies.FixedReply,
    binding: Optional[BenjiSmsBinding],
    now: datetime,
) -> bool:
    """Send a no-conversation reply unless the number already had one today."""
    # Checked first so that a day's claim is not spent on a reply no gate would let out.
    if not can_send_fixed_reply():
        return False
    if not BenjiSmsStrangerReply.objects.claim(number_hash, now):
        return False
    return _send_fixed(inbound, reply, binding, now, for_screen=False)


def handle_inbound(inbound: Inbound, now: Optional[datetime] = None) -> Result:
    """Decide what one inbound text gets, and do it. The table is in the module docstring.

    Raises whatever the queue raises when a turn or a media deletion cannot be queued;
    the view turns that into a 503 so Twilio posts the text again.
    """
    now = now or timezone.now()

    try:
        number_hash: Optional[str] = phone_hash(inbound.sender)
    except InvalidPhoneNumber:
        number_hash = None
    phone = BenjiSmsPhone.objects.filter(phone_hash=number_hash).first() if number_hash else None
    newest = phone.newest_binding() if phone is not None else None

    if inbound.num_media > 0:
        # Whoever sent it and whatever happens next: images are never kept.
        enqueue_media_deletion(inbound.sid, newest.conversation_id if newest is not None else None)

    if number_hash is None:
        return Result(Outcome.NOT_A_PHONE)

    keyword = classify(inbound.body, inbound.opt_out_type)

    if phone is None:
        if keyword is not None:
            return Result(Outcome.STRANGER_KEYWORD)
        return Result(Outcome.STRANGER, _send_daily(inbound, number_hash, replies.STRANGER, None, now))

    if keyword is not None and keyword.keyword is Keyword.STOP:
        newly_revoked = phone.revoke(now)
        replied = False
        if newly_revoked and not keyword.carrier:
            # The one send to a revoked number: the confirmation of the revocation.
            replied = _send_fixed(inbound, replies.STOP, newest, now, for_screen=True)
        return Result(Outcome.STOPPED, replied)

    if phone.revoked_at is not None:
        if keyword is None or keyword.keyword is not Keyword.START:
            return Result(Outcome.REVOKED)
        cleared, resumed = phone.clear_revocation(now)
        replied = False
        if cleared and not keyword.carrier:
            reply = replies.START_RESUMED if resumed else replies.START_REENTRY
            replied = _send_fixed(inbound, reply, newest, now, for_screen=True)
        return Result(Outcome.STARTED, replied)

    if keyword is not None and keyword.keyword is Keyword.HELP:
        replied = False
        if not keyword.carrier:
            replied = _send_fixed(inbound, replies.HELP, newest, now, for_screen=True)
        return Result(Outcome.HELP, replied)

    if keyword is not None and keyword.keyword is Keyword.START and not keyword.also_plain_text:
        # Nothing to clear. Not a question for the model either.
        return Result(Outcome.START_IGNORED)

    if phone.is_shared(now):
        return Result(Outcome.SHARED, _send_daily(inbound, number_hash, replies.SHARED, newest, now))

    binding = phone.active_binding()
    if binding is not None and binding.is_quiet(now):
        binding.end(AssistantConversationStatus.EXPIRED)
        binding = None
    if binding is None:
        return Result(Outcome.REENTRY, _send_daily(inbound, number_hash, replies.REENTRY, newest, now))

    if not channel_enabled(binding.white_label):
        # A turn would pay for a reply that no gate would let out.
        return Result(Outcome.CHANNEL_OFF)

    binding.touch_inbound(now)

    if inbound.num_media > 0:
        return Result(Outcome.PICTURE, _send_fixed(inbound, replies.PICTURE, binding, now, for_screen=True))

    if not inbound.body.strip():
        return Result(Outcome.EMPTY)

    enqueue_turn(binding.conversation_id, inbound.sid)
    return Result(Outcome.QUEUED)


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
    is read from the database. Answers with empty TwiML: every reply goes out through
    the REST API, so each one has a delivery row.

    The fallback URL is where Twilio posts a text after the primary URL failed. It runs
    the same handling, which is safe because a replay sends nothing new, and logs
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
        except Exception as exc:
            # The class only: an exception's text can quote a key, and this view's
            # locals hold the number and the message. 503 has Twilio post it again.
            logger.error("Benji SMS inbound webhook failed: %s", f"{type(exc).__module__}.{type(exc).__qualname__}")
            return _twiml(503)

        # The only trace of a decision that sends nothing (revoked, channel off, a second
        # text that day). WARNING, as in benji_sms.py: this logger has no handler of its
        # own and the root level drops INFO, so anything lower never reaches the logs.
        logger.warning("Benji SMS inbound: outcome=%s replied=%s", result.outcome.value, result.replied)
        return _twiml()
