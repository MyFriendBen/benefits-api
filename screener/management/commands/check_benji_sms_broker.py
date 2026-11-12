"""Alarms on the Benji SMS broker (MFB-2436). Run every 10 minutes by Heroku Scheduler.

Checks the dedicated Celery broker (CELERY_BROKER_URL), never the cache Redis:

- memory: used_memory as a share of maxmemory. The broker runs `noeviction`, so a full
  broker refuses new jobs and the inbound webhook starts failing.
- queue depth: ready jobs on the benji_sms queue. A backlog means the worker is down,
  scaled to zero, or slower than the inbound rate.
- policy: anything other than `noeviction` would drop queued jobs silently.
- reachability: a broker that does not answer, or no broker configured at all.

Each alarm is one ERROR log line, which Sentry turns into an event and the Scheduler
dyno's log shows; the message names this command, so an alarm traces back here. Counts
and settings only. Every run also prints one summary line, alarm or not.

Thresholds are options so an alarm can be fired on purpose: `--memory-threshold 0
--depth-threshold 0` fires both on any broker (the "both alarms fire on a test" check).
"""

import logging
from typing import Any

import redis
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from benefits.celery_config import broker_client_kwargs, queue_list_names
from screener.tasks import BENJI_SMS_QUEUE

logger = logging.getLogger(__name__)

# Share of maxmemory. Jobs are a few hundred bytes each, so the broker should sit near
# its empty footprint; crossing this means something is accumulating.
DEFAULT_MEMORY_THRESHOLD = 0.7

# Ready jobs. A healthy worker drains the queue within a turn or two; this many waiting
# is minutes of texts going unanswered.
DEFAULT_DEPTH_THRESHOLD = 25

ALARM_PREFIX = "Benji SMS broker alarm (check_benji_sms_broker)"


class Command(BaseCommand):
    help = "Alarm on the Benji SMS broker's memory, queue depth, eviction policy and reachability."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--memory-threshold",
            type=float,
            default=DEFAULT_MEMORY_THRESHOLD,
            help=f"Alarm when used memory is at least this share of maxmemory (default {DEFAULT_MEMORY_THRESHOLD}).",
        )
        parser.add_argument(
            "--depth-threshold",
            type=int,
            default=DEFAULT_DEPTH_THRESHOLD,
            help=f"Alarm when at least this many jobs are waiting (default {DEFAULT_DEPTH_THRESHOLD}).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        url = settings.CELERY_BROKER_URL
        if not url:
            self._alarm("no broker is configured (CELERY_BROKER_URL is empty).")
            return

        try:
            client = redis.Redis.from_url(url, **broker_client_kwargs(url))
            memory = client.info("memory")
            depth = sum(client.llen(name) for name in queue_list_names(BENJI_SMS_QUEUE))
        except redis.RedisError as exc:
            # The class only: a connection error's message can carry the host.
            self._alarm(f"the broker did not answer ({type(exc).__name__}).")
            return

        used = int(memory.get("used_memory", 0))
        maxmemory = int(memory.get("maxmemory", 0))
        policy = memory.get("maxmemory_policy", "unknown")
        share = used / maxmemory if maxmemory else None

        if policy != "noeviction":
            self._alarm(f"maxmemory-policy is {policy}, not noeviction; queued jobs can be evicted.")
        if share is not None and share >= options["memory_threshold"]:
            self._alarm(
                f"memory at {share:.0%} of maxmemory ({used} of {maxmemory} bytes), "
                f"threshold {options['memory_threshold']:.0%}."
            )
        if depth >= options["depth_threshold"]:
            self._alarm(
                f"{depth} job(s) waiting on {BENJI_SMS_QUEUE}, threshold {options['depth_threshold']}. "
                "Check that the worker is up (heroku ps)."
            )

        share_text = f"{share:.0%}" if share is not None else "no maxmemory set"
        self.stdout.write(f"Benji SMS broker: memory {used} bytes ({share_text}), policy {policy}, {depth} waiting.")

    def _alarm(self, detail: str) -> None:
        logger.error("%s: %s", ALARM_PREFIX, detail)
