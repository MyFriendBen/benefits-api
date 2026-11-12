"""Benji SMS background jobs (MFB-2436; MFB-1916 proposal v3, decision 5).

ONE QUEUE, ONE TASK. Every job runs on the `benji_sms` queue, consumed by the
`worker` process type (Procfile) through the dedicated broker (benefits/celery_config.py).
`benji_sms_turn` is the job: generate and send the reply to one inbound text. The
inbound webhook (MFB-2439) enqueues it through `enqueue_turn`; its body is MFB-2440.
`benji_sms_ping` is not a second job but a probe: it runs under the same policy, so
`manage.py benji_sms_worker_check` proves the path a turn takes.

PAYLOADS CARRY IDS ONLY: the conversation id and the inbound Twilio MessageSid. Never
message text, the phone number or its hash (privacy companion §2). The worker reads
`From` from the message at Twilio when it sends.

AT LEAST ONCE. Jobs are acknowledged after they run and handed out again if the
worker dies mid-job (settings: CELERY_TASK_ACKS_LATE), so a turn can run twice. The
turn absorbs that by sending the inbound SID to ai-service as `client_message_id`
(ai-service answers a repeat with the stored reply) and by checking the delivery row
before sending. A job is delivered at most MAX_DELIVERIES times, counted on the broker,
so one that kills its worker every time cannot loop.

RETRIES. Connection failures, timeouts and `TransientTurnError` are retried once, after
a fixed backoff: two attempts, the proposal's working figure. Anything else fails
at once. A job that fails its last attempt is dead-lettered: a `BenjiSmsDeadLetter`
row with ids and the error's class, and an ERROR log that reaches Sentry. So is a job
whose retry cannot be queued, and one delivered too many times.

SENTRY AND LOGS. Celery prints a job's arguments in its own log lines ("Task ...
received"), which Sentry also keeps as breadcrumbs; the turn task publishes with the SID
masked in that printed form (`argsrepr`), retries included. Sentry's Celery integration
attaches each job's arguments and stack locals to its events, and benefits/sentry_scrub.py
strips those from every Celery event and redacts anything shaped like a MessageSid from
every event, wherever it appears (exception text, breadcrumbs, request URLs).
"""

import logging
import re
import uuid
from typing import Any, Optional

import redis
import requests
from celery import Task, shared_task
from celery.exceptions import Reject
from celery.result import AsyncResult
from celery.utils.saferepr import saferepr
from django.conf import settings

from benefits.celery_config import broker_client_kwargs

from .models import BenjiSmsDeadLetter

logger = logging.getLogger(__name__)

BENJI_SMS_QUEUE = "benji_sms"

# A Twilio message SID: SM (SMS) or MM (MMS), then 32 lowercase hex digits.
MESSAGE_SID_RE = re.compile(r"\A(SM|MM)[0-9a-f]{32}\Z")

# Two attempts in all, RETRY_BACKOFF_SECONDS apart (Celery's retry_backoff is
# base * 2**retries, so the one retry waits the base). No jitter: Celery's is "full",
# a random wait between 0 and the backoff, and a second attempt fired straight after a
# timeout mostly times out too. With one retry there is no herd to spread.
MAX_RETRIES = 1
RETRY_BACKOFF_SECONDS = 5
RETRY_BACKOFF_MAX_SECONDS = 30

# Per attempt. A turn makes one ai-service call, AI_SERVICE_WORKER_TIMEOUT (35s,
# screener/assistant.py), and up to three Twilio calls at 10s each (read the inbound's
# `From`, send the disclosure on a first reply, send the reply), plus the database:
# about 65s at worst. The soft limit raises SoftTimeLimitExceeded inside the job, which
# fails it through on_failure and so dead-letters it. MFB-2440: a soft limit that lands
# during or after a Twilio send is BenjiSmsDeliveryUnknown, not a clean failure; the
# reply may be out, so no resend and no apology. The hard limit kills the worker child,
# and Celery then skips on_failure: it logs "Hard time limit (95s) exceeded for ..." at
# ERROR (Sentry sees it) but writes no dead-letter row. Only a job that swallows the soft limit, or
# hangs where Python cannot interrupt it, gets that far. The broker's visibility_timeout
# (settings) must outlast the longest a fetched job can stay unacknowledged, or a slow
# job is handed out twice: the retry countdown, then a wait for a free child (up to one
# attempt), then its own attempt. That is RETRY_BACKOFF_SECONDS + 2 * TIME_LIMIT_SECONDS.
SOFT_TIME_LIMIT_SECONDS = 80
TIME_LIMIT_SECONDS = 95

# Deliveries of one job before it is dead-lettered unrun: its two attempts, plus one
# redelivery after a lost worker (a deploy or a crash mid-job). Only a job that keeps
# killing its worker child reaches the cap, which CELERY_TASK_REJECT_ON_WORKER_LOST would
# otherwise requeue forever.
MAX_DELIVERIES = MAX_RETRIES + 2
# The count lives on the broker under this prefix, and expires well after any job could
# still be redelivered (the visibility timeout is 300s).
DELIVERY_COUNT_PREFIX = "benji_sms:deliveries:"
DELIVERY_COUNT_TTL_SECONDS = 3600


class TransientTurnError(Exception):
    """A failure worth a second attempt that requests would not raise on its own.

    For the turn to raise on, e.g., a 5xx from ai-service or a retryable Twilio error.
    Its message never reaches the dead-letter row, but it does reach logs and Sentry,
    so it must not quote message text, numbers or hashes.
    """


class TooManyDeliveries(Exception):
    """The job was handed out MAX_DELIVERIES times without finishing."""


class BrokerNotConfigured(RuntimeError):
    """No broker is attached and tasks are not eager, so a job would go nowhere."""


RETRYABLE_ERRORS = (TransientTurnError, requests.ConnectionError, requests.Timeout)


def _uuid_or_none(value: Any) -> Optional[str]:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def _sid_or_none(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and MESSAGE_SID_RE.match(value) else None


_broker_client: Optional[redis.Redis] = None


def _count_delivery(task_id: str) -> int:
    """Count one more delivery of this job on the broker, and return the total."""
    global _broker_client
    url = settings.CELERY_BROKER_URL
    if _broker_client is None:
        _broker_client = redis.Redis.from_url(url, **broker_client_kwargs(url))
    key = f"{DELIVERY_COUNT_PREFIX}{task_id}"
    pipe = _broker_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, DELIVERY_COUNT_TTL_SECONDS)
    count, _ = pipe.execute()
    return int(count)


class BenjiSmsTask(Task):
    """Retry and dead-letter policy shared by every job on the Benji SMS queue."""

    autoretry_for = RETRYABLE_ERRORS
    max_retries = MAX_RETRIES
    retry_backoff = RETRY_BACKOFF_SECONDS
    retry_backoff_max = RETRY_BACKOFF_MAX_SECONDS
    retry_jitter = False
    soft_time_limit = SOFT_TIME_LIMIT_SECONDS
    time_limit = TIME_LIMIT_SECONDS

    def dead_letter_ids(self, args: tuple, kwargs: dict) -> tuple[Optional[str], Optional[str]]:
        """(conversation id, inbound SID) for this job's dead-letter row. None for jobs
        that carry neither."""
        return None, None

    def before_start(self, task_id: str, args: tuple, kwargs: dict) -> None:
        """Refuse a job delivered more than MAX_DELIVERIES times.

        Raising here fails the job through on_failure, so it is dead-lettered without
        running. Skipped in eager mode, where nothing is delivered. If the broker cannot
        count (it is full or down), the job runs: a count is not worth a lost reply.
        """
        if self.request.is_eager or not settings.CELERY_BROKER_URL:
            return
        try:
            deliveries = _count_delivery(task_id)
        except redis.RedisError as exc:
            logger.warning("Benji SMS job %s: delivery not counted (%s).", task_id, type(exc).__name__)
            return
        if deliveries > MAX_DELIVERIES:
            raise TooManyDeliveries(f"Delivered {deliveries} times; the cap is {MAX_DELIVERIES}.")

    def retry(
        self,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        exc: Optional[BaseException] = None,
        throw: bool = True,
        eta: Any = None,
        countdown: Optional[float] = None,
        max_retries: Optional[int] = None,
        **options: Any,
    ) -> Any:
        """Celery's retry, plus a dead letter when the next attempt cannot be queued.

        When publishing the retry fails (a full or unreachable broker), Celery raises
        Reject(requeue=False): the message is deleted and on_failure never runs, so the
        job would vanish with no row and no alarm.
        """
        try:
            return super().retry(
                args=args,
                kwargs=kwargs,
                exc=exc,
                throw=throw,
                eta=eta,
                countdown=countdown,
                max_retries=max_retries,
                **options,
            )
        except Reject as reject:
            request = self.request
            self.dead_letter(
                exc if exc is not None else reject.reason,
                request.id,
                tuple(request.args or ()),
                dict(request.kwargs or {}),
            )
            raise

    def on_failure(self, exc: BaseException, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """Celery calls this once per job, when it fails for good: a retryable error on
        the last attempt, or any other error on any attempt. Earlier attempts go through
        on_retry instead."""
        self.dead_letter(exc, task_id, args, kwargs)

    def dead_letter(self, exc: BaseException, task_id: str, args: tuple, kwargs: dict) -> None:
        """Record the job as failed for good, and raise the alarm."""
        attempts = self.request.retries + 1
        error_type = f"{type(exc).__module__}.{type(exc).__qualname__}"
        conversation_id, inbound_sid = self.dead_letter_ids(args, kwargs)
        # Never let recording the failure raise out of the failure handler: Celery would
        # log that error in place of the job's own.
        try:
            dead_letter = BenjiSmsDeadLetter.objects.record(
                task_name=self.name,
                task_id=task_id,
                attempts=attempts,
                error_type=error_type,
                conversation_id=conversation_id,
                inbound_sid=inbound_sid,
            )
        except Exception:
            logger.exception(
                "Benji SMS job %s (%s) failed every attempt and could not be dead-lettered.", task_id, self.name
            )
            return
        # The alarm. Ids and the error class only: no SID (it resolves to the number at
        # Twilio) and no exception message.
        logger.error(
            "Benji SMS job dead-lettered: %s failed %d attempt(s) with %s (dead letter %s, task %s, conversation %s).",
            self.name,
            attempts,
            error_type,
            dead_letter.pk,
            task_id,
            dead_letter.conversation_id,
        )


# What a MessageSid argument prints as in Celery's log lines and task events.
MASKED_SID = "<MessageSid>"


def _mask_sid(value: Any) -> Any:
    return MASKED_SID if _sid_or_none(value) else value


class BenjiSmsTurnTask(BenjiSmsTask):
    def apply_async(
        self, args: Optional[tuple] = None, kwargs: Optional[dict] = None, *rest: Any, **options: Any
    ) -> AsyncResult:
        """Publish with the SID masked in the printed form of the arguments.

        Celery logs `argsrepr` ("Task ... received") and Sentry keeps those lines as
        breadcrumbs. A retry publishes a fresh message through here too, and Celery does
        not carry the first message's argsrepr over, so masking at enqueue alone would
        let the retry print the SID.
        """
        options.setdefault("argsrepr", saferepr(tuple(_mask_sid(arg) for arg in (args or ()))))
        options.setdefault("kwargsrepr", saferepr({key: _mask_sid(value) for key, value in (kwargs or {}).items()}))
        return super().apply_async(args, kwargs, *rest, **options)

    def dead_letter_ids(self, args: tuple, kwargs: dict) -> tuple[Optional[str], Optional[str]]:
        conversation_id = kwargs.get("conversation_id", args[0] if len(args) > 0 else None)
        message_sid = kwargs.get("message_sid", args[1] if len(args) > 1 else None)
        return _uuid_or_none(conversation_id), _sid_or_none(message_sid)


def _turn_payload(conversation_id: Any, message_sid: Any) -> tuple[str, str]:
    """The job's two arguments, normalized. Raises ValueError on anything else, without
    echoing the value."""
    conversation = _uuid_or_none(conversation_id)
    if conversation is None:
        raise ValueError("conversation_id must be a UUID.")
    sid = _sid_or_none(message_sid)
    if sid is None:
        raise ValueError("message_sid must be a Twilio message SID (SM or MM, then 32 hex digits).")
    return conversation, sid


@shared_task(base=BenjiSmsTurnTask, name="screener.benji_sms_turn", queue=BENJI_SMS_QUEUE)
def benji_sms_turn(conversation_id: str, message_sid: str) -> None:
    """Generate and send Benji's reply to one inbound text.

    The turn itself is MFB-2440. Until it lands this fails closed: a job enqueued by
    mistake is dead-lettered, never dropped and never answered.
    """
    _turn_payload(conversation_id, message_sid)
    raise NotImplementedError("The Benji SMS turn lands in MFB-2440.")


@shared_task(base=BenjiSmsTask, name="screener.benji_sms_ping", queue=BENJI_SMS_QUEUE, ignore_result=False)
def benji_sms_ping(fail: bool = False) -> str:
    """Probe for benji_sms_worker_check. `fail` raises a retryable error on every attempt,
    so the job is retried and then dead-lettered exactly as a failing turn would be."""
    if fail:
        raise TransientTurnError("Forced failure from benji_sms_worker_check --fail.")
    return "pong"


def require_broker() -> None:
    """Raise BrokerNotConfigured unless a job would actually reach a worker.

    Without a broker URL Celery falls back to an AMQP broker on localhost, and a publish
    fails with a connection-refused error that does not name the missing setting.
    """
    if not settings.CELERY_TASK_ALWAYS_EAGER and not settings.CELERY_BROKER_URL:
        raise BrokerNotConfigured("CELERY_BROKER_URL is not set and Celery is not in eager mode.")


def enqueue_turn(conversation_id: Any, message_sid: Any) -> AsyncResult:
    """Queue the reply to one inbound text. The only way the webhook starts a turn.

    Raises ValueError on a payload that is not a conversation id and a MessageSid, and
    BrokerNotConfigured when there is nowhere to send it.
    """
    conversation, sid = _turn_payload(conversation_id, message_sid)
    require_broker()
    return benji_sms_turn.apply_async(args=(conversation, sid), queue=BENJI_SMS_QUEUE)
