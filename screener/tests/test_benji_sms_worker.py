"""The Benji SMS worker and its dedicated broker (MFB-2436).

What these pin: the broker wiring never touches the cache Redis and copes with Heroku's
TLS; jobs carry ids only; retryable failures get a second attempt and everything else
fails at once; a job that fails its last attempt leaves exactly one dead-letter row with
ids and the error class (never the error's message), and that row follows its
conversation on deletion, in the ORM and in raw SQL; the broker alarms fire on the
conditions they name; the worker check reports what it proved; and the ai-service client
takes a per-call timeout without changing the web path's.

Tests run Celery eagerly (pytest.ini), so a job runs inside the call that queues it.
"""

import importlib
import logging
import ssl
import uuid
from io import StringIO
from typing import Any
from unittest import mock

import pytest
import redis
import requests
from celery.exceptions import TimeoutError as CeleryTimeoutError
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from kombu import Connection, Exchange, Producer, Queue

from benefits.celery import app as celery_app
from benefits.celery_config import broker_client_kwargs, broker_use_ssl, queue_list_names
from screener import assistant
from screener.models import AssistantConversation, AssistantMessage, BenjiSmsDeadLetter
from screener.tasks import (
    BENJI_SMS_QUEUE,
    MAX_RETRIES,
    BenjiSmsTask,
    BrokerNotConfigured,
    TransientTurnError,
    benji_sms_ping,
    benji_sms_turn,
    enqueue_turn,
)
from screener.tests.assistant_helpers import make_conversation, make_message

MIGRATION_0163 = importlib.import_module("screener.migrations.0163_assistant_message_db_cascade")
MIGRATION_0174 = importlib.import_module("screener.migrations.0174_benji_sms_dead_letter_db_cascade")

SID = "SM" + "ab" * 16
MMS_SID = "MM" + "0" * 32
TASKS_LOGGER = "screener.tasks"
BROKER_LOGGER = "screener.management.commands.check_benji_sms_broker"


# A job that fails with a requests timeout on its first attempt and succeeds on its
# second, to show a retryable failure is retried rather than dead-lettered.
_flaky_attempts: list[int] = []


@celery_app.task(base=BenjiSmsTask, name="screener.tests.flaky_once", ignore_result=False)
def flaky_once() -> str:
    _flaky_attempts.append(1)
    if len(_flaky_attempts) == 1:
        raise requests.Timeout("first attempt times out")
    return "ok"


class TestBrokerConfig(SimpleTestCase):
    def test_heroku_tls_url_turns_verification_off(self) -> None:
        self.assertEqual(broker_use_ssl("rediss://:pw@host:6380"), {"ssl_cert_reqs": ssl.CERT_NONE})
        self.assertIsNone(broker_client_kwargs("rediss://:pw@host:6380")["ssl_cert_reqs"])

    def test_plain_url_takes_no_ssl_options(self) -> None:
        """redis-py raises at connect if a plain connection is handed ssl_cert_reqs."""
        self.assertIsNone(broker_use_ssl("redis://localhost:6379/0"))
        self.assertNotIn("ssl_cert_reqs", broker_client_kwargs("redis://localhost:6379/0"))

    def test_client_kwargs_bound_every_socket_operation(self) -> None:
        kwargs = broker_client_kwargs("redis://localhost:6379/0")
        self.assertEqual(kwargs["socket_timeout"], kwargs["socket_connect_timeout"])
        self.assertLessEqual(kwargs["socket_timeout"], 5)

    def test_queue_lists_cover_every_priority_step(self) -> None:
        self.assertEqual(
            queue_list_names("benji_sms"),
            ["benji_sms", "benji_sms\x06\x163", "benji_sms\x06\x166", "benji_sms\x06\x169"],
        )

    def test_jobs_are_acknowledged_late_one_at_a_time_as_json(self) -> None:
        conf = celery_app.conf
        self.assertTrue(conf.task_acks_late)
        self.assertTrue(conf.task_reject_on_worker_lost)
        self.assertEqual(conf.worker_prefetch_multiplier, 1)
        self.assertEqual(conf.accept_content, ["json"])
        self.assertEqual(conf.task_default_queue, BENJI_SMS_QUEUE)

    def test_the_second_attempt_waits_a_fixed_backoff(self) -> None:
        """Full jitter could fire the retry at once, straight into the same timeout."""
        self.assertFalse(benji_sms_turn.retry_jitter)
        self.assertEqual(benji_sms_turn.max_retries, 1)
        self.assertGreaterEqual(benji_sms_turn.retry_backoff, 5)

    def test_a_redelivered_job_cannot_overtake_a_running_one(self) -> None:
        """The visibility timeout must outlast one attempt plus the retry countdown."""
        visibility = celery_app.conf.broker_transport_options["visibility_timeout"]
        self.assertGreater(visibility, benji_sms_turn.time_limit + benji_sms_turn.retry_backoff_max)


@pytest.mark.skipif(not settings.REDIS_URL, reason="needs a Redis server (REDIS_URL)")
class TestQueueListsAgainstKombu(SimpleTestCase):
    """The depth alarm counts the lists kombu really writes, priorities included."""

    def test_depth_counts_messages_of_every_priority(self) -> None:
        url = settings.REDIS_URL
        name = f"test_benji_sms_depth_{uuid.uuid4().hex}"
        client = redis.Redis.from_url(url, **broker_client_kwargs(url))
        self.addCleanup(client.delete, *queue_list_names(name))
        queue = Queue(name, Exchange(name, type="direct"), routing_key=name)
        with Connection(url, transport_options={"ssl_cert_reqs": None} if url.startswith("rediss") else {}) as conn:
            producer = Producer(conn)
            for priority in (None, 9):
                producer.publish(
                    {"n": 1}, exchange=queue.exchange, routing_key=name, declare=[queue], priority=priority
                )

        self.assertEqual(sum(client.llen(key) for key in queue_list_names(name)), 2)
        self.assertEqual(client.llen(name), 1)


class TestPing(TestCase):
    def test_round_trips(self) -> None:
        self.assertEqual(benji_sms_ping.delay().get(timeout=1), "pong")
        self.assertFalse(BenjiSmsDeadLetter.objects.exists())

    def test_runs_under_the_turn_policy(self) -> None:
        for attribute in ("autoretry_for", "max_retries", "retry_backoff", "time_limit", "soft_time_limit"):
            with self.subTest(attribute=attribute):
                self.assertEqual(getattr(benji_sms_ping, attribute), getattr(benji_sms_turn, attribute))
        self.assertEqual(benji_sms_ping.queue, benji_sms_turn.queue)


class TestRetriesAndDeadLetter(TestCase):
    def setUp(self) -> None:
        _flaky_attempts.clear()

    def assertFailedWith(self, result: Any, exc_type: type) -> None:
        """Eager jobs keep their failure on the result, as a worker's would."""
        self.assertTrue(result.failed())
        self.assertIsInstance(result.result, exc_type)

    def test_a_forced_failure_is_retried_then_dead_lettered_once(self) -> None:
        task_id = str(uuid.uuid4())
        with self.assertLogs(TASKS_LOGGER, level="ERROR") as logs:
            result = benji_sms_ping.apply_async(kwargs={"fail": True}, task_id=task_id)

        self.assertFailedWith(result, TransientTurnError)
        dead_letter = BenjiSmsDeadLetter.objects.get()
        self.assertEqual(dead_letter.task_id, task_id)
        self.assertEqual(dead_letter.task_name, "screener.benji_sms_ping")
        self.assertEqual(dead_letter.attempts, MAX_RETRIES + 1)
        self.assertEqual(dead_letter.error_type, "screener.tasks.TransientTurnError")
        self.assertIsNone(dead_letter.conversation_id)
        self.assertIsNone(dead_letter.inbound_sid)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("dead-lettered", logs.output[0])
        self.assertIn(str(dead_letter.pk), logs.output[0])

    def test_a_retryable_failure_that_then_succeeds_leaves_no_dead_letter(self) -> None:
        self.assertEqual(flaky_once.delay().get(timeout=1), "ok")
        self.assertEqual(len(_flaky_attempts), 2)
        self.assertFalse(BenjiSmsDeadLetter.objects.exists())

    def test_the_turn_fails_closed_at_once_until_mfb_2440(self) -> None:
        conversation = make_conversation(channel="sms")
        with self.assertLogs(TASKS_LOGGER, level="ERROR"):
            result = benji_sms_turn.delay(str(conversation.pk), SID)

        self.assertFailedWith(result, NotImplementedError)
        dead_letter = BenjiSmsDeadLetter.objects.get()
        self.assertEqual(dead_letter.attempts, 1)
        self.assertEqual(dead_letter.task_name, "screener.benji_sms_turn")
        self.assertEqual(dead_letter.error_type, "builtins.NotImplementedError")
        self.assertEqual(dead_letter.conversation_id, conversation.pk)
        self.assertEqual(dead_letter.inbound_sid, SID)

    def test_the_alarm_names_ids_but_not_the_sid_or_the_error_message(self) -> None:
        conversation = make_conversation(channel="sms")
        with self.assertLogs(TASKS_LOGGER, level="ERROR") as logs:
            benji_sms_turn.delay(str(conversation.pk), SID)

        self.assertIn(str(conversation.pk), logs.output[0])
        self.assertNotIn(SID, logs.output[0])
        self.assertNotIn("MFB-2440", logs.output[0])

    def test_a_conversation_deleted_while_queued_leaves_no_sid_behind(self) -> None:
        with self.assertLogs(TASKS_LOGGER, level="ERROR"):
            benji_sms_turn.delay(str(uuid.uuid4()), SID)

        dead_letter = BenjiSmsDeadLetter.objects.get()
        self.assertIsNone(dead_letter.conversation_id)
        self.assertIsNone(dead_letter.inbound_sid)

    def test_a_malformed_payload_is_dead_lettered_without_its_values(self) -> None:
        with self.assertLogs(TASKS_LOGGER, level="ERROR"):
            result = benji_sms_turn.delay("not-a-uuid", "+13035550100")

        self.assertFailedWith(result, ValueError)
        self.assertNotIn("+13035550100", str(result.result))
        dead_letter = BenjiSmsDeadLetter.objects.get()
        self.assertEqual(dead_letter.error_type, "builtins.ValueError")
        self.assertIsNone(dead_letter.conversation_id)
        self.assertIsNone(dead_letter.inbound_sid)

    def test_a_failure_to_record_is_logged_and_the_job_still_fails(self) -> None:
        with (
            mock.patch.object(BenjiSmsDeadLetter.objects, "record", side_effect=RuntimeError("db down")),
            self.assertLogs(TASKS_LOGGER, level="ERROR") as logs,
        ):
            result = benji_sms_ping.apply_async(kwargs={"fail": True})

        self.assertFailedWith(result, TransientTurnError)
        self.assertIn("could not be dead-lettered", logs.output[0])
        self.assertFalse(BenjiSmsDeadLetter.objects.exists())


class TestEnqueueTurn(TestCase):
    def test_refuses_anything_but_a_conversation_id_and_a_message_sid(self) -> None:
        conversation_id = uuid.uuid4()
        cases = {
            "conversation is not a uuid": ("123", SID),
            "sid is a phone number": (conversation_id, "+13035550100"),
            "sid is message text": (conversation_id, "please stop texting me"),
            "sid has the wrong prefix": (conversation_id, "CA" + "0" * 32),
            "sid is uppercase hex": (conversation_id, "SM" + "AB" * 16),
            "sid is too short": (conversation_id, "SM" + "0" * 31),
        }
        for name, (conversation, sid) in cases.items():
            with self.subTest(name), mock.patch.object(benji_sms_turn, "apply_async") as apply_async:
                with self.assertRaises(ValueError):
                    enqueue_turn(conversation, sid)
                apply_async.assert_not_called()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False, CELERY_BROKER_URL="redis://broker:6379/0")
    def test_queues_ids_only_on_the_benji_sms_queue(self) -> None:
        conversation_id = uuid.uuid4()
        for sid in (SID, MMS_SID):
            with self.subTest(sid=sid), mock.patch.object(benji_sms_turn, "apply_async") as apply_async:
                enqueue_turn(conversation_id, sid)

                apply_async.assert_called_once_with(args=(str(conversation_id), sid), queue=BENJI_SMS_QUEUE)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False, CELERY_BROKER_URL="")
    def test_refuses_without_a_broker_rather_than_hanging_on_localhost(self) -> None:
        with mock.patch.object(benji_sms_turn, "apply_async") as apply_async:
            with self.assertRaises(BrokerNotConfigured):
                enqueue_turn(uuid.uuid4(), SID)
            apply_async.assert_not_called()

    def test_runs_in_process_when_eager(self) -> None:
        conversation = make_conversation(channel="sms")
        with self.assertLogs(TASKS_LOGGER, level="ERROR"):
            result = enqueue_turn(conversation.pk, SID)

        self.assertTrue(result.failed())
        self.assertEqual(BenjiSmsDeadLetter.objects.get().conversation_id, conversation.pk)


class TestDeadLetterTable(TestCase):
    def test_a_sid_needs_a_conversation(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            BenjiSmsDeadLetter.objects.create(
                task_name="screener.benji_sms_turn", task_id="t", attempts=1, error_type="x", inbound_sid=SID
            )

    def test_rows_go_with_their_conversation(self) -> None:
        conversation = make_conversation(channel="sms")
        BenjiSmsDeadLetter.objects.record(
            task_name="screener.benji_sms_turn",
            task_id="t",
            attempts=2,
            error_type="requests.exceptions.Timeout",
            conversation_id=str(conversation.pk),
            inbound_sid=SID,
        )

        conversation.delete()

        self.assertFalse(BenjiSmsDeadLetter.objects.exists())


class TestDeadLetterDatabaseCascade(TransactionTestCase):
    """Migration 0174's SQL, run for real, as test_benji_sms_tables does for 0172.

    pytest runs with `--nomigrations`, so the test schema has no database-level cascade
    until the SQL is applied here (see TestDatabaseLevelCascade there for why autocommit).
    """

    def setUp(self) -> None:
        self.addCleanup(self._restore_no_action)

    def _restore_no_action(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0174._DROP_DB_CASCADE)
            cursor.execute(MIGRATION_0163._DROP_DB_CASCADE)

    def _delete_type(self) -> str:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT c.confdeltype FROM pg_constraint c "
                "WHERE c.conrelid = 'screener_benjismsdeadletter'::regclass AND c.contype = 'f'"
            )
            return cursor.fetchone()[0]

    def _seed(self) -> AssistantConversation:
        conversation = make_conversation(channel="sms")
        make_message(conversation, seq=0)
        BenjiSmsDeadLetter.objects.record(
            task_name="screener.benji_sms_turn",
            task_id="t",
            attempts=2,
            error_type="requests.exceptions.Timeout",
            conversation_id=str(conversation.pk),
            inbound_sid=SID,
        )
        return conversation

    def _raw_delete(self, conversation_id: uuid.UUID) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM screener_assistantconversation WHERE conversation_id = %s", [str(conversation_id)]
            )

    def test_the_test_database_starts_without_the_cascade(self) -> None:
        self.assertEqual(self._delete_type(), "a")

    def test_a_raw_delete_of_the_conversation_takes_its_dead_letters(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0163._ADD_DB_CASCADE)
            cursor.execute(MIGRATION_0174._ADD_DB_CASCADE)
        conversation = self._seed()

        self._raw_delete(conversation.pk)

        self.assertFalse(AssistantMessage.objects.exists())
        self.assertFalse(BenjiSmsDeadLetter.objects.exists())

    def test_a_raw_delete_fails_without_the_migration(self) -> None:
        """0174 is load-bearing: with only 0163, the dead letter blocks the delete."""
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0163._ADD_DB_CASCADE)
        conversation = self._seed()

        with self.assertRaises(IntegrityError):
            self._raw_delete(conversation.pk)

    def test_reverse_sql_restores_no_action(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0174._ADD_DB_CASCADE)
        self.assertEqual(self._delete_type(), "c")

        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0174._DROP_DB_CASCADE)

        self.assertEqual(self._delete_type(), "a")


def _fake_broker(
    used: int = 1_000_000, maxmemory: int = 25_000_000, policy: str = "noeviction", depth: int = 0
) -> mock.Mock:
    client = mock.Mock()
    client.info.return_value = {"used_memory": used, "maxmemory": maxmemory, "maxmemory_policy": policy}
    client.llen.side_effect = lambda name: depth if name == BENJI_SMS_QUEUE else 0
    return client


@override_settings(CELERY_BROKER_URL="rediss://:secret@broker.example:6380")
class TestBrokerAlarms(SimpleTestCase):
    def _run(self, client: Any, *args: str) -> tuple[str, list[str]]:
        stdout = StringIO()
        with (
            mock.patch("redis.Redis.from_url", return_value=client) as from_url,
            self.assertLogs(BROKER_LOGGER, level="DEBUG") as logs,
        ):
            # assertLogs needs one record; this one is filtered out below.
            logging.getLogger(BROKER_LOGGER).debug("start")
            call_command("check_benji_sms_broker", *args, stdout=stdout, stderr=StringIO())
        self.from_url = from_url
        return stdout.getvalue(), [r.getMessage() for r in logs.records if r.levelno >= logging.ERROR]

    def test_a_healthy_broker_raises_no_alarm(self) -> None:
        output, alarms = self._run(_fake_broker())

        self.assertEqual(alarms, [])
        self.assertIn("policy noeviction, 0 waiting", output)

    def test_reaches_heroku_redis_over_tls_without_verification(self) -> None:
        self._run(_fake_broker())

        url, kwargs = self.from_url.call_args.args[0], self.from_url.call_args.kwargs
        self.assertEqual(url, "rediss://:secret@broker.example:6380")
        self.assertIsNone(kwargs["ssl_cert_reqs"])

    def test_memory_alarm(self) -> None:
        _, alarms = self._run(_fake_broker(used=20_000_000, maxmemory=25_000_000))

        self.assertEqual(len(alarms), 1)
        self.assertIn("memory at 80% of maxmemory", alarms[0])
        self.assertIn("check_benji_sms_broker", alarms[0])

    def test_queue_depth_alarm(self) -> None:
        _, alarms = self._run(_fake_broker(depth=40))

        self.assertEqual(len(alarms), 1)
        self.assertIn("40 job(s) waiting on benji_sms", alarms[0])

    def test_depth_counts_every_priority_list(self) -> None:
        client = _fake_broker()
        client.llen.side_effect = lambda name: 10
        _, alarms = self._run(client)

        self.assertIn("40 job(s) waiting", alarms[0])

    def test_an_evicting_policy_alarms(self) -> None:
        _, alarms = self._run(_fake_broker(policy="allkeys-lru"))

        self.assertEqual(len(alarms), 1)
        self.assertIn("allkeys-lru, not noeviction", alarms[0])

    def test_zero_thresholds_fire_both_alarms_on_any_broker(self) -> None:
        """How staging proves the alarms reach Sentry."""
        _, alarms = self._run(_fake_broker(), "--memory-threshold", "0", "--depth-threshold", "0")

        self.assertEqual(len(alarms), 2)
        self.assertTrue(any("memory at" in alarm for alarm in alarms))
        self.assertTrue(any("waiting on benji_sms" in alarm for alarm in alarms))

    def test_no_maxmemory_means_no_memory_alarm(self) -> None:
        """A local Redis has no maxmemory; the share is undefined, not 100%."""
        output, alarms = self._run(_fake_broker(maxmemory=0))

        self.assertEqual(alarms, [])
        self.assertIn("no maxmemory set", output)

    def test_an_unreachable_broker_alarms_with_the_error_class_only(self) -> None:
        client = mock.Mock()
        client.info.side_effect = redis.ConnectionError("Error connecting to broker.example:6380 secret")
        _, alarms = self._run(client)

        self.assertEqual(len(alarms), 1)
        self.assertIn("did not answer (ConnectionError)", alarms[0])
        self.assertNotIn("broker.example", alarms[0])
        self.assertNotIn("secret", alarms[0])

    @override_settings(CELERY_BROKER_URL="")
    def test_no_broker_configured_alarms(self) -> None:
        _, alarms = self._run(mock.Mock())

        self.assertEqual(len(alarms), 1)
        self.assertIn("no broker is configured", alarms[0])
        self.from_url.assert_not_called()


class TestWorkerCheck(TestCase):
    def test_round_trip_in_eager_mode_says_so(self) -> None:
        stdout = StringIO()
        call_command("benji_sms_worker_check", stdout=stdout)

        self.assertIn("Eager mode", stdout.getvalue())
        self.assertIn("Round trip OK", stdout.getvalue())

    def test_fail_reports_the_dead_letter(self) -> None:
        stdout = StringIO()
        with self.assertLogs(TASKS_LOGGER, level="ERROR"):
            call_command("benji_sms_worker_check", "--fail", stdout=stdout)

        dead_letter = BenjiSmsDeadLetter.objects.get()
        self.assertIn(f"dead letter {dead_letter.pk}", stdout.getvalue())
        self.assertIn(f"after {MAX_RETRIES + 1} attempt(s)", stdout.getvalue())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False, CELERY_BROKER_URL="")
    def test_refuses_without_a_broker(self) -> None:
        with self.assertRaisesMessage(CommandError, "CELERY_BROKER_URL is not set"):
            call_command("benji_sms_worker_check", stdout=StringIO())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False, CELERY_BROKER_URL="redis://broker:6379/0")
    def test_a_worker_that_never_answers_is_a_failure(self) -> None:
        result = mock.Mock(id="task-1")
        result.get.side_effect = CeleryTimeoutError()
        with (
            mock.patch.object(benji_sms_ping, "apply_async", return_value=result),
            self.assertRaisesMessage(CommandError, "Is the worker scaled up?"),
        ):
            call_command("benji_sms_worker_check", "--timeout", "0.1", stdout=StringIO())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False, CELERY_BROKER_URL="redis://broker:6379/0")
    def test_fail_with_no_dead_letter_in_time_is_a_failure(self) -> None:
        with (
            mock.patch.object(benji_sms_ping, "apply_async"),
            mock.patch("screener.management.commands.benji_sms_worker_check.POLL_SECONDS", 0.01),
            self.assertRaisesMessage(CommandError, "No dead-letter row"),
        ):
            call_command("benji_sms_worker_check", "--fail", "--timeout", "0.05", stdout=StringIO())


class TestAiServiceTimeout(SimpleTestCase):
    def test_the_web_path_keeps_its_budget(self) -> None:
        with mock.patch("screener.assistant.requests.request") as request:
            request.return_value.json.return_value = {}
            request.return_value.status_code = 200
            assistant._proxy("GET", "/conversations", params={"screen_id": "x"})

        self.assertEqual(request.call_args.kwargs["timeout"], assistant.AI_SERVICE_TIMEOUT)

    def test_a_caller_can_pass_the_worker_budget(self) -> None:
        with mock.patch("screener.assistant.requests.request") as request:
            assistant.ai_service_request(
                "POST", "/conversations/x/messages", json_body={}, timeout=assistant.AI_SERVICE_WORKER_TIMEOUT
            )

        self.assertEqual(request.call_args.kwargs["timeout"], assistant.AI_SERVICE_WORKER_TIMEOUT)
        self.assertGreater(assistant.AI_SERVICE_WORKER_TIMEOUT, assistant.AI_SERVICE_TIMEOUT)

    def test_the_worker_budget_fits_inside_one_attempt(self) -> None:
        self.assertLess(assistant.AI_SERVICE_WORKER_TIMEOUT, benji_sms_turn.soft_time_limit)
