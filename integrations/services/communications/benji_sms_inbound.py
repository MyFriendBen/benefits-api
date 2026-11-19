"""What the Benji SMS inbound webhook does with one text (MFB-2439).

Design: MFB-1916 proposal v3, decisions 3, 4, 5, 7 and 10. Runbook: docs/BENJI_SMS_INBOUND.md.
The view that receives Twilio's post is `screener.benji_sms_inbound`; this module decides
what state the sending number is in, and either answers with a fixed reply or queues a
turn for the worker. It never calls the model.

WHAT HAPPENS TO A TEXT. In order, first match wins:

 1. Sender is not a phone number     nothing (a short code or an alphanumeric sender)
 2. Unknown number, our HELP word    the stranger reply, once a day (it says who we are)
 3. Unknown number, other keyword    nothing: Twilio answered its own, and there is no
                                     row to revoke or restart
 4. Unknown number                   the stranger reply, once a day
 5. STOP                             revoke the number, close its conversation
 6. START, revoked                   clear the revocation; resume the conversation the
                                     STOP closed, if it can
 7. START, not revoked               nothing ("yes" is an ordinary answer and carries on)
 8. Revoked, anything else           nothing
 9. HELP                             the HELP reply
10. Marked shared                    the shared-phone reply, once a day
11. Quiet past the interval          expire the conversation, then as 12
12. No active conversation           the re-entry reply, once a day
13. Channel off for the white label  nothing
14. Has media                        the "can't read pictures" reply
15. Otherwise                        queue the turn

Then, for any text that carries media, whatever happened above: queue the deletion of the
media at Twilio. It comes last so that a broker outage cannot block a STOP: the state
change is made first, and the failed queueing still answers 503, so Twilio posts again
and the deletion is queued on the replay.

STOP comes before every other state on purpose: a shared or expired number that texts
STOP must still be revoked. STOP and START are decided under the phone's row lock
(`BenjiSmsPhone.revoke`, `clear_revocation`), never on the snapshot read at the start,
so a STOP and a START sent together are applied in order. Every other branch re-reads
the revocation just before it sends or queues anything (`is_revoked_now`), so a STOP
that lands while a text is being handled stops its reply. The send itself is not under
the lock, so a STOP landing in the last milliseconds before it can still be beaten; the
worker (MFB-2440) checks again before every reply.

WHO ANSWERS A KEYWORD. Twilio answers its own keywords itself and blocks our sends after
a STOP, so for those we only change state. Our fixed STOP, HELP and START replies go out
for the wordings Twilio does not handle (benji_sms_keywords.py).

A REPLAYED WEBHOOK CHANGES NOTHING NEW. Twilio posts a text again when it does not get our
answer in time, and through the fallback URL after that.
- Every fixed reply first inserts its delivery row, which the database allows once per
  inbound MessageSid (`BenjiSmsDelivery.objects.claim_fixed`), and a replay claims
  nothing else: not the day's no-conversation reply either.
- Every STOP and START, including one that changed nothing, leaves a receipt with its
  MessageSid in the same locked transaction (`BenjiSmsKeywordReceipt`), and a text with
  a receipt is not applied again: a replay of an older one cannot undo a newer one. The
  receipt says what the first post did, so a replay can still send a confirmation the
  first post never got to; the fixed-reply claim stops a second one.
- A replayed turn is queued again and absorbed by the worker, which sends the SID to
  ai-service as `client_message_id` (MFB-2440).

SENDS ARE BEST EFFORT, THE QUEUE IS NOT. A fixed reply Twilio refuses is logged and
dropped: the webhook still answers 200, because the state change is what matters and a
retry would not send it either. When the refusal may pass (Twilio unreachable, 429, 5xx),
the day's no-conversation claim is given back, so the number's next text can try again.
A turn or a media deletion that cannot be queued raises, and the view answers 503.

NOTHING HERE LOGS THE NUMBER, ITS HASH OR THE TEXT. Log lines carry the reply's label
and Twilio's error code.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from django.utils import timezone

from screener.models import (
    AssistantConversationStatus,
    BenjiSmsBinding,
    BenjiSmsDelivery,
    BenjiSmsPhone,
    BenjiSmsStrangerReply,
)
from screener.tasks import enqueue_media_deletion, enqueue_turn

from . import benji_sms_replies as replies
from .benji_sms import (
    BenjiSmsDeliveryUnknown,
    BenjiSmsSendError,
    can_send_fixed_reply,
    channel_enabled,
    send_fixed_reply,
    send_screen_sms,
    status_callback_url,
)
from .benji_sms_hash import InvalidPhoneNumber, phone_hash
from .benji_sms_keywords import Keyword, KeywordMatch, classify

logger = logging.getLogger(__name__)

# Twilio's error for a send to a number that opted out with a carrier keyword. Expected
# whenever our keyword list and Twilio's disagree about a wording, so not an alarm.
TWILIO_OPTED_OUT = 21610
# Twilio's "too many requests". Like a 5xx or no answer at all, it may pass.
TOO_MANY_REQUESTS = 429


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


def _may_pass(exc: BenjiSmsSendError) -> bool:
    """Whether a refused send failed for a reason that may pass: Twilio never answered,
    is rate limiting, or is failing. A 4xx about the number itself will not change."""
    return exc.status is None or exc.status == TOO_MANY_REQUESTS or exc.status >= 500


def _deliver(
    inbound: Inbound,
    delivery: BenjiSmsDelivery,
    body: str,
    reply: replies.FixedReply,
    binding: Optional[BenjiSmsBinding],
    now: datetime,
    *,
    for_screen: bool,
) -> tuple[bool, bool]:
    """Send a fixed reply whose delivery row is already claimed. Returns (sent, may_retry).

    `may_retry` is True only when the text definitely did not go out, for a reason that
    may pass: a gate refused it, or Twilio was unreachable, rate limiting or failing.
    The delivery row is deleted whenever nothing went out, and kept when the outcome is
    unknown, so a replay never sends a second one.

    `for_screen` replies belong to a conversation and are held to its white label's
    flag; the others (stranger, shared, re-entry) answer a number that has none.
    """
    callback = status_callback_url()
    try:
        if for_screen and binding is not None:
            outbound_sid = send_screen_sms(
                inbound.sender, body, white_label=binding.white_label, status_callback=callback
            )
        else:
            outbound_sid = send_fixed_reply(inbound.sender, body, status_callback=callback)
    except BenjiSmsSendError as exc:
        delivery.delete()
        log = logger.warning if exc.code == TWILIO_OPTED_OUT else logger.error
        log("Benji SMS fixed reply not sent: reply=%s status=%s code=%s", reply.label, exc.status, exc.code)
        return False, _may_pass(exc)
    except BenjiSmsDeliveryUnknown as exc:
        # It may have gone out. The row stays, with no outbound SID, so a replay does
        # not send a second one.
        logger.error("Benji SMS fixed reply delivery unknown: reply=%s cause=%s", reply.label, exc.cause)
        return False, False

    if outbound_sid is None:
        # Refused by a gate (kill switch, flag, DEBUG), which logged why.
        delivery.delete()
        return False, True

    delivery.outbound_sid = outbound_sid
    delivery.sent_at = now
    delivery.save(update_fields=["outbound_sid", "sent_at"])
    return True, False


def _send_fixed(
    inbound: Inbound,
    reply: replies.FixedReply,
    binding: Optional[BenjiSmsBinding],
    now: datetime,
    *,
    for_screen: bool,
) -> bool:
    """Send one fixed reply to the sender, at most once per inbound. True if it went."""
    # The text first: a failed lookup then leaves no claim behind, and a replay can send.
    body = replies.reply_text(reply, _locale(binding))
    delivery = BenjiSmsDelivery.objects.claim_fixed(inbound.sid, binding)
    if delivery is None:
        return False
    sent, _ = _deliver(inbound, delivery, body, reply, binding, now, for_screen=for_screen)
    return sent


def _send_daily(
    inbound: Inbound,
    number_hash: str,
    reply: replies.FixedReply,
    binding: Optional[BenjiSmsBinding],
    now: datetime,
) -> bool:
    """Send a no-conversation reply unless the number already had one today.

    Claims the inbound's fixed reply before the day's: a replay of a text that was
    already answered (or refused for the day) never spends the number's allowance.
    """
    # Checked first so that a day's claim is not spent on a reply no gate would let out.
    if not can_send_fixed_reply():
        return False
    body = replies.reply_text(reply, _locale(binding))
    delivery = BenjiSmsDelivery.objects.claim_fixed(inbound.sid, binding)
    if delivery is None:
        return False
    if not BenjiSmsStrangerReply.objects.claim(number_hash, now):
        delivery.delete()
        return False
    sent, may_retry = _deliver(inbound, delivery, body, reply, binding, now, for_screen=False)
    if may_retry:
        BenjiSmsStrangerReply.objects.release(number_hash, now)
    return sent


def _from_a_stranger(inbound: Inbound, number_hash: str, keyword: Optional[KeywordMatch], now: datetime) -> Result:
    """A number with no phone row: it never used the on-ramp."""
    if keyword is None or (keyword.keyword is Keyword.HELP and not keyword.carrier):
        # Twilio does not answer our HELP words ("ayuda"), and the stranger reply is the
        # help we have for a number we know nothing about: who we are, and STOP.
        return Result(Outcome.STRANGER, _send_daily(inbound, number_hash, replies.STRANGER, None, now))
    # Twilio answered its own keywords. Our STOP and START words have nothing to change:
    # we never text a stranger unprompted, and there is no conversation to restart.
    return Result(Outcome.STRANGER_KEYWORD)


def _decide(inbound: Inbound, now: datetime, number_hash: Optional[str], phone: Optional[BenjiSmsPhone]) -> Result:
    """Rows 1 to 15 of the table in the module docstring."""
    if number_hash is None:
        return Result(Outcome.NOT_A_PHONE)

    keyword = classify(inbound.body, inbound.opt_out_type)

    if phone is None:
        return _from_a_stranger(inbound, number_hash, keyword, now)

    newest = phone.newest_binding()

    if keyword is not None and keyword.keyword is Keyword.STOP:
        revoked = phone.revoke(now, inbound.sid)
        replied = False
        if revoked and not keyword.carrier:
            # The one send to a revoked number: the confirmation of the revocation.
            # Also tried on a replay of this STOP, in case the first post never got to
            # send it; the fixed-reply claim keeps it to one.
            replied = _send_fixed(inbound, replies.STOP, newest, now, for_screen=True)
        return Result(Outcome.STOPPED, replied)

    if keyword is not None and keyword.keyword is Keyword.START:
        # Decided under the phone's row lock, not on the snapshot above.
        cleared, resumed = phone.clear_revocation(now, inbound.sid)
        if cleared:
            replied = False
            if not keyword.carrier:
                reply = replies.START_RESUMED if resumed else replies.START_REENTRY
                replied = _send_fixed(inbound, reply, newest, now, for_screen=True)
            return Result(Outcome.STARTED, replied)
        if phone.revoked_at is not None:
            # A replay of a START that changed nothing, after a newer STOP.
            return Result(Outcome.REVOKED)
        if not keyword.also_plain_text:
            # Nothing to clear. Not a question for the model either.
            return Result(Outcome.START_IGNORED)
        # "yes" from a number that was not revoked: an ordinary answer, carry on.

    if phone.revoked_at is not None:
        return Result(Outcome.REVOKED)

    if keyword is not None and keyword.keyword is Keyword.HELP:
        replied = False
        if not keyword.carrier:
            if phone.is_revoked_now():
                return Result(Outcome.REVOKED)
            replied = _send_fixed(inbound, replies.HELP, newest, now, for_screen=True)
        return Result(Outcome.HELP, replied)

    if phone.is_shared(now):
        if phone.is_revoked_now():
            return Result(Outcome.REVOKED)
        return Result(Outcome.SHARED, _send_daily(inbound, number_hash, replies.SHARED, newest, now))

    # The newest binding is the only one that can be active (BenjiSmsPhone.newest_binding).
    binding = newest if newest is not None and newest.status == AssistantConversationStatus.ACTIVE else None
    channel_on = binding is not None and channel_enabled(binding.white_label)
    # Expires a quiet conversation, and records the text otherwise, under a row lock. A
    # text for a white label that is switched off is not recorded: nothing answers it.
    if binding is not None and not binding.record_inbound(now, touch=channel_on):
        binding = None
    # Before anything goes out: a STOP from the same number may have landed since the
    # snapshot (and closed the binding record_inbound just found ended).
    if phone.is_revoked_now():
        return Result(Outcome.REVOKED)
    if binding is None:
        return Result(Outcome.REENTRY, _send_daily(inbound, number_hash, replies.REENTRY, newest, now))

    if not channel_on:
        # A turn would pay for a reply that no gate would let out.
        return Result(Outcome.CHANNEL_OFF)

    if inbound.num_media > 0:
        return Result(Outcome.PICTURE, _send_fixed(inbound, replies.PICTURE, binding, now, for_screen=True))

    if not inbound.body.strip():
        return Result(Outcome.EMPTY)

    enqueue_turn(binding.conversation_id, inbound.sid)
    return Result(Outcome.QUEUED)


class MediaDeletionNotQueued(Exception):
    """The text was handled, but deleting its media could not be queued.

    Carries the decision so the view can still log it before answering 503. Never
    carries the number, the text or the SID.
    """

    def __init__(self, result: Result, cause: str) -> None:
        self.result = result
        self.cause = cause
        super().__init__(f"Media deletion not queued after outcome={result.outcome.value}: {cause}")


def handle_inbound(inbound: Inbound, now: Optional[datetime] = None) -> Result:
    """Decide what one inbound text gets, and do it. The table is in the module docstring.

    Raises when a turn or a media deletion cannot be queued, and the view answers 503 so
    Twilio posts the text again; everything done before the raise is safe to repeat on
    that replay. A failed media deletion raises `MediaDeletionNotQueued`, carrying the
    decision that was already carried out.
    """
    now = now or timezone.now()
    phone: Optional[BenjiSmsPhone] = None
    result: Optional[Result] = None
    try:
        try:
            number_hash: Optional[str] = phone_hash(inbound.sender)
        except InvalidPhoneNumber:
            number_hash = None
        phone = BenjiSmsPhone.objects.filter(phone_hash=number_hash).first() if number_hash else None
        result = _decide(inbound, now, number_hash, phone)
        return result
    finally:
        if inbound.num_media > 0:
            _queue_media_deletion(inbound, phone, result)


def _queue_media_deletion(inbound: Inbound, phone: Optional[BenjiSmsPhone], result: Optional[Result]) -> None:
    """Whoever sent it and whatever was decided, even if deciding failed: images are
    never kept. Runs after the decision, so a broker outage cannot block a STOP."""
    try:
        newest = phone.newest_binding() if phone is not None else None
        enqueue_media_deletion(inbound.sid, newest.conversation_id if newest is not None else None)
    except Exception as exc:
        cause = f"{type(exc).__module__}.{type(exc).__qualname__}"
        if result is None:
            # Deciding failed too, and its error is the one already on its way to the
            # view (and to a 503). Keep it; record this one by class only.
            logger.error("Benji SMS media deletion not queued: %s", cause)
            return
        raise MediaDeletionNotQueued(result, cause) from None
