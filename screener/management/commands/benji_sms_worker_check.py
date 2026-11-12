"""Prove the Benji SMS worker path end to end (MFB-2436).

    python manage.py benji_sms_worker_check          # a ping round-trips through the worker
    python manage.py benji_sms_worker_check --fail   # a forced failure is retried, then dead-lettered

The ping runs under the turn's retry and dead-letter policy (screener/tasks.py), so a
pass proves the path a real turn takes: publish, broker, worker, result. With the worker
scaled to zero the ping waits on the queue and this times out; the ping runs whenever a
worker next starts, which is harmless.

In eager mode (local, DEBUG) the ping runs in this process and no broker is involved;
the output says so.
"""

import time
import uuid
from typing import Any

from celery.exceptions import TimeoutError as CeleryTimeoutError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from screener.models import BenjiSmsDeadLetter
from screener.tasks import BENJI_SMS_QUEUE, BrokerNotConfigured, benji_sms_ping, require_broker

DEFAULT_TIMEOUT_SECONDS = 60
POLL_SECONDS = 1


class Command(BaseCommand):
    help = "Round-trip a ping through the Benji SMS worker, or with --fail, prove a failure is dead-lettered."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--fail",
            action="store_true",
            help="Send a ping that fails every attempt, and wait for its dead-letter row.",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=DEFAULT_TIMEOUT_SECONDS,
            help=f"Seconds to wait (default {DEFAULT_TIMEOUT_SECONDS}).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            require_broker()
        except BrokerNotConfigured as exc:
            raise CommandError(str(exc))
        if settings.CELERY_TASK_ALWAYS_EAGER:
            self.stdout.write("Eager mode: the ping runs in this process, not on a worker.")
        if options["fail"]:
            self._check_dead_letter(options["timeout"])
        else:
            self._check_round_trip(options["timeout"])

    def _check_round_trip(self, timeout: float) -> None:
        started = time.monotonic()
        result = benji_sms_ping.apply_async(queue=BENJI_SMS_QUEUE)
        try:
            value = result.get(timeout=timeout)
        except CeleryTimeoutError:
            raise CommandError(
                f"No answer from the worker in {timeout:.0f}s (task {result.id}). Is the worker scaled up?"
            )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if value != "pong":
            raise CommandError(f"Unexpected answer from the ping (task {result.id}).")
        self.stdout.write(self.style.SUCCESS(f"Round trip OK in {elapsed_ms} ms (task {result.id})."))

    def _check_dead_letter(self, timeout: float) -> None:
        task_id = str(uuid.uuid4())
        # In eager mode every attempt runs inside this call, so the row already exists.
        benji_sms_ping.apply_async(kwargs={"fail": True}, task_id=task_id, queue=BENJI_SMS_QUEUE)
        deadline = time.monotonic() + timeout
        while True:
            dead_letter = BenjiSmsDeadLetter.objects.filter(task_id=task_id).first()
            if dead_letter is not None:
                break
            if time.monotonic() >= deadline:
                raise CommandError(
                    f"No dead-letter row for task {task_id} after {timeout:.0f}s. Is the worker scaled up?"
                )
            time.sleep(POLL_SECONDS)
        self.stdout.write(
            self.style.SUCCESS(
                f"Forced failure dead-lettered after {dead_letter.attempts} attempt(s): "
                f"dead letter {dead_letter.pk}, task {task_id}, {dead_letter.error_type}."
            )
        )
