"""Tests for the Benji conversation tables.

These tables are unusual: Django owns the schema, mfb-ai-service is the runtime
writer (see screener/models.AssistantConversation). So the constraints are the
contract between the two repos, and these tests are what pin them. If a constraint
here is relaxed, ai-service's Postgres store loses a guarantee it relies on.
"""

import importlib
import uuid
from datetime import timedelta

from django.contrib.admin.sites import AdminSite
from django.db import IntegrityError, connection, transaction
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.utils import timezone

from authentication.models import User
from screener.admin import AssistantConversationAdmin
from screener.models import AssistantConversation, AssistantMessage, WhiteLabel
from screener.tests.assistant_helpers import make_conversation, make_message

# Migration 0163 turns the message foreign key into a database-level ON DELETE
# CASCADE. Imported by name because the module starts with a digit, so the plain
# `import` statement cannot reach it.
MIGRATION_0163 = importlib.import_module("screener.migrations.0163_assistant_message_db_cascade")
# Migration 0170 keeps a database-level DEFAULT on `channel`; same import reason.
MIGRATION_0170 = importlib.import_module("screener.migrations.0170_assistant_conversation_channel")

# Kept as a named constant rather than inlined into cursor.execute(): a multiline
# string as the sole argument to a call is formatted one way by black 24 (split onto
# its own line) and the opposite way by black 25+ (hugged to the parens), so inline it
# fails `black --check` for someone regardless of which form is committed. CI runs
# psf/black@stable, i.e. whatever is newest.
FK_DELETE_TYPE_SQL = """
SELECT confdeltype FROM pg_constraint
WHERE conrelid = 'screener_assistantmessage'::regclass AND contype = 'f'
"""

# The INSERT ai-service ran before it knew about `channel` (store_postgres.py at
# ai-service d3f3477), minus the columns that have defaults or are nullable.
INSERT_WITHOUT_CHANNEL_SQL = """
INSERT INTO screener_assistantconversation
    (conversation_id, screen_uuid, status, context, created_at, updated_at)
VALUES (%s, %s, 'active', '{}', %s, %s)
"""


class TestAssistantConversationConstraints(TestCase):
    def test_one_active_conversation_per_screen(self):
        """The per-screen idempotency ai-service's API documents, enforced in the DB.

        Per screen AND channel; both of these are web conversations.

        `POST /v1/conversations` is "find the active conversation for this screen, else
        create one" — a read-then-write race that two tabs or a retry can lose.
        """
        screen_uuid = uuid.uuid4()
        make_conversation(screen_uuid=screen_uuid)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_conversation(screen_uuid=screen_uuid)

    def test_web_and_sms_conversations_coexist_on_one_screen(self):
        """The constraint is per channel since MFB-2432.

        A texted conversation is its own row on the same screen as the web one
        (MFB-1916 proposal v2, decision 3), so both being active is the intended
        state, not a lost race.
        """
        screen_uuid = uuid.uuid4()
        make_conversation(screen_uuid=screen_uuid, channel="web")
        make_conversation(screen_uuid=screen_uuid, channel="sms")

        self.assertEqual(
            set(
                AssistantConversation.objects.filter(screen_uuid=screen_uuid, status="active").values_list(
                    "channel", flat=True
                )
            ),
            {"web", "sms"},
        )

    def test_one_active_sms_conversation_per_screen(self):
        """Per channel still means one: the SMS side gets the same race protection."""
        screen_uuid = uuid.uuid4()
        make_conversation(screen_uuid=screen_uuid, channel="sms")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_conversation(screen_uuid=screen_uuid, channel="sms")

    def test_channel_outside_the_vocabulary_is_rejected(self):
        """ai-service writes with raw SQL, so the model's choices never see its inserts."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_conversation(channel="email")

    def test_closed_conversations_do_not_block_a_new_one(self):
        """The constraint is partial for a reason: history must be able to accumulate.

        A screen whose earlier conversation was closed has to be able to open another,
        or closing one would lock the household out of the assistant permanently.
        """
        screen_uuid = uuid.uuid4()
        make_conversation(screen_uuid=screen_uuid, status="closed")
        make_conversation(screen_uuid=screen_uuid, status="closed")

        active = make_conversation(screen_uuid=screen_uuid)

        self.assertEqual(AssistantConversation.objects.filter(screen_uuid=screen_uuid).count(), 3)
        self.assertEqual(active.status, "active")

    def test_seq_is_unique_within_a_conversation(self):
        """Backstop for ai-service's MAX(seq)+1 assignment across multiple dynos."""
        conversation = make_conversation()
        make_message(conversation, seq=0)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_message(conversation, seq=0, role="assistant")

    def test_same_seq_in_different_conversations_is_fine(self):
        first, second = make_conversation(), make_conversation()

        make_message(first, seq=0)
        make_message(second, seq=0)

        self.assertEqual(AssistantMessage.objects.filter(seq=0).count(), 2)

    def test_client_message_id_is_unique_within_a_conversation(self):
        """Idempotent retries depend on this: one client id, one stored exchange."""
        conversation = make_conversation()
        make_message(conversation, seq=0, client_message_id="abc")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_message(conversation, seq=1, client_message_id="abc")

    def test_many_messages_without_a_client_id_coexist(self):
        """Why the client-id constraint has to be partial.

        Most turns carry no client id. Under a plain unique constraint every NULL row
        after the first would collide, which would break ordinary conversation.
        """
        conversation = make_conversation()
        for seq in range(4):
            make_message(conversation, seq=seq)

        self.assertEqual(conversation.messages.count(), 4)

    def test_orm_delete_of_a_conversation_removes_its_messages(self):
        """Covers Django's Python-level cascade only — NOT migration 0163.

        `on_delete=models.CASCADE` makes the ORM collect and delete children itself,
        so this passes with or without a database-level cascade. The migration's own
        SQL is covered by TestDatabaseLevelCascade below.
        """
        conversation = make_conversation()
        make_message(conversation, seq=0)
        make_message(conversation, seq=1, role="assistant")

        conversation.delete()

        self.assertEqual(AssistantMessage.objects.count(), 0)

    def test_context_round_trips_as_json(self):
        """The snapshot the prompt is rebuilt from on every turn, so it has to survive
        storage intact — nested lists and all."""
        context = {
            "household": {"size": 4},
            "eligible_programs": [{"external_name": "co_snap", "name": "SNAP", "estimated_value": 9600}],
            "current_programs": [],
            "results_url": "https://example.test/co/abc/results/benefits",
        }
        conversation = make_conversation(context=context)

        self.assertEqual(AssistantConversation.objects.get(pk=conversation.pk).context, context)

    def test_timestamps_are_not_orm_managed(self):
        """No auto_now/auto_now_add, on purpose.

        Those are ORM-level behaviors and would do nothing on ai-service's inserts,
        leaving NULL created_at and an updated_at frozen at creation. An explicit value
        has to be preserved exactly.
        """
        stamp = timezone.now() - timedelta(days=30)
        conversation = make_conversation(created_at=stamp, updated_at=stamp)

        stored = AssistantConversation.objects.get(pk=conversation.pk)
        self.assertEqual(stored.created_at, stamp)
        self.assertEqual(stored.updated_at, stamp)


class TestChannelDatabaseDefault(TestCase):
    """Migration 0170's DEFAULT 'web', which is what makes its deploy order safe.

    benefits-api migrates before ai-service learns the column exists, and until then
    ai-service's raw-SQL INSERT names no channel. Without a database-level default that
    insert fails on NOT NULL and nobody can start a conversation.

    As with 0163 below, the migration's SQL has to be applied here: pytest runs with
    `--nomigrations`, so the test schema comes from the models, and Django 4.2 cannot
    express a database default in a model. A plain `TestCase` is enough, unlike 0163:
    the ALTER runs before any insert, and the test transaction rolls it back.
    """

    def _insert_without_channel(self) -> uuid.UUID:
        conversation_id = uuid.uuid4()
        with connection.cursor() as cursor:
            cursor.execute(
                INSERT_WITHOUT_CHANNEL_SQL,
                [conversation_id, uuid.uuid4(), timezone.now(), timezone.now()],
            )
        return conversation_id

    def test_the_test_database_starts_without_the_default(self):
        """Guards against the test below passing without the migration's SQL."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._insert_without_channel()

    def test_an_insert_that_names_no_channel_is_a_web_conversation(self):
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0170._SET_DB_DEFAULT)

        conversation_id = self._insert_without_channel()

        self.assertEqual(AssistantConversation.objects.get(conversation_id=conversation_id).channel, "web")


class TestRollbackGuard(TestCase):
    """Reversing 0170 is refused, with instructions, while a non-web conversation is active.

    Without the guard the reverse dies on a duplicate key while re-creating the old
    one-active-per-screen index, or, on a screen with only an SMS conversation, succeeds
    and lets the previous ai-service resume the texts as the widget's conversation.
    """

    def _guard(self) -> None:
        MIGRATION_0170._refuse_rollback_while_non_web_is_active(None, connection.schema_editor())

    def test_rollback_is_refused_while_a_screen_has_web_and_sms_active(self):
        screen_uuid = uuid.uuid4()
        make_conversation(screen_uuid=screen_uuid, channel="web")
        sms = make_conversation(screen_uuid=screen_uuid, channel="sms")

        with self.assertRaisesMessage(RuntimeError, str(sms.conversation_id)):
            self._guard()

    def test_rollback_is_refused_for_an_active_sms_conversation_on_its_own(self):
        """The old index would build, but the old ai-service would show the texts in the widget."""
        make_conversation(channel="sms")

        with self.assertRaises(RuntimeError):
            self._guard()

    def test_rollback_is_allowed_once_the_sms_conversation_is_closed(self):
        screen_uuid = uuid.uuid4()
        make_conversation(screen_uuid=screen_uuid, channel="web")
        make_conversation(screen_uuid=screen_uuid, channel="sms", status="closed")

        self._guard()


class TestChannelSurvivesRollback(TestCase):
    """Reversing 0170 drops `channel`; re-applying it must not relabel texts as web.

    The column itself can't be dropped and re-added inside a test, so this runs the
    two statements that carry the value across: the stash the reverse runs before the
    column goes, and the restore the forward runs after it is back (when every row has
    just been backfilled with the default, simulated here by setting it to 'web').
    """

    def _run(self, sql: str) -> None:
        with connection.cursor() as cursor:
            cursor.execute(sql)

    def test_a_closed_sms_conversation_is_still_sms_after_rollback_and_reapply(self):
        sms = make_conversation(channel="sms", status="closed")
        web = make_conversation(channel="web")

        self._run(MIGRATION_0170._STASH_CHANNEL)
        AssistantConversation.objects.filter(pk=sms.pk).update(channel="web")  # the re-applied default
        self._run(MIGRATION_0170._RESTORE_CHANNEL)

        sms.refresh_from_db()
        web.refresh_from_db()
        self.assertEqual(sms.channel, "sms")
        self.assertEqual(web.channel, "web")

    def test_the_stash_leaves_no_trace_in_the_context(self):
        sms = make_conversation(channel="sms", status="closed")
        original = dict(sms.context)

        self._run(MIGRATION_0170._STASH_CHANNEL)
        self._run(MIGRATION_0170._RESTORE_CHANNEL)

        sms.refresh_from_db()
        self.assertEqual(sms.context, original)

    def test_the_forward_restore_is_a_no_op_on_a_first_migration(self):
        web = make_conversation(channel="web")

        self._run(MIGRATION_0170._RESTORE_CHANNEL)

        web.refresh_from_db()
        self.assertEqual(web.channel, "web")


class TestDatabaseLevelCascade(TransactionTestCase):
    """Migration 0163's SQL, exercised for real against Postgres.

    This has to apply the migration's SQL itself. pytest runs with `--nomigrations`
    (see pytest.ini), so the test schema is built from the models and no `RunSQL` ever
    executes — the foreign key in the test database has NO database-level cascade.
    Without this class, 0163 had zero coverage: the ORM-delete test above passes
    either way, so dropping or breaking the migration left the suite green and the
    failure surfaced only on the path 0163 exists for — a raw `DELETE`, which is how
    mfb-ai-service (no ORM) and any future bulk deletion would do it.

    Importing `_ADD_DB_CASCADE` rather than restating the SQL is the point: what gets
    tested is the string the migration actually runs.

    `TransactionTestCase`, not `TestCase`, for two reasons that are the same reason —
    the transaction a `TestCase` wraps each test in distorts precisely what is under
    test here. Postgres refuses `ALTER TABLE` on a table with pending deferred-FK
    trigger events ("cannot ALTER TABLE ... because it has pending trigger events"),
    which any prior ORM insert leaves behind; and Django's foreign keys are DEFERRABLE
    INITIALLY DEFERRED, so inside an open transaction both the violation and the
    cascade action fire at commit rather than at the statement, which is not how
    production behaves. Running in autocommit costs a table flush per test and buys
    semantics that match the deployed database.
    """

    def setUp(self):
        # Autocommit means the DDL below is NOT rolled back at the end of the test, so
        # it has to be undone explicitly or it leaks into every later test sharing this
        # database. Registered before anything runs, so it also covers a failure
        # partway through. `_DROP_DB_CASCADE` is safe to run whether or not the cascade
        # was ever applied — it restores the constraint to NO ACTION either way.
        self.addCleanup(self._restore_no_action)

    def _restore_no_action(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0163._DROP_DB_CASCADE)

    def _apply_cascade(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0163._ADD_DB_CASCADE)

    def _delete_type(self) -> str:
        """`pg_constraint.confdeltype` for the message FK: 'a' = no action, 'c' = cascade."""
        with connection.cursor() as cursor:
            cursor.execute(FK_DELETE_TYPE_SQL)
            return cursor.fetchone()[0]

    def _raw_delete(self, conversation_id) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM screener_assistantconversation WHERE conversation_id = %s",
                [str(conversation_id)],
            )

    def test_the_test_database_starts_without_the_cascade(self):
        """Guards against this whole class becoming vacuous.

        If `--nomigrations` were ever dropped, the constraint would already be a
        cascade and the tests below would pass without proving anything. Then this
        assertion fails and tells you to simplify rather than silently over-claiming.
        """
        self.assertEqual(self._delete_type(), "a")

    def test_migration_sql_converts_the_fk_to_cascade(self):
        self._apply_cascade()

        self.assertEqual(self._delete_type(), "c")

    def test_raw_sql_delete_cascades_once_the_migration_has_run(self):
        """The behavior the migration is for: a DELETE issued outside the ORM.

        The cascade is applied before any row exists, because Postgres will not ALTER a
        table that has pending deferred-FK trigger events from an earlier insert.
        """
        self._apply_cascade()
        conversation = make_conversation()
        make_message(conversation, seq=0)
        make_message(conversation, seq=1, role="assistant")

        self._raw_delete(conversation.pk)

        self.assertEqual(AssistantMessage.objects.count(), 0)
        self.assertEqual(AssistantConversation.objects.count(), 0)

    def test_raw_sql_delete_fails_without_the_migration(self):
        """Proves the migration is load-bearing rather than decorative — this is what
        production would do on a raw delete if 0163 were missing."""
        conversation = make_conversation()
        make_message(conversation, seq=0)

        with self.assertRaises(IntegrityError):
            self._raw_delete(conversation.pk)

    def test_reverse_sql_restores_no_action(self):
        """0163 has to be reversible — `migrate screener 0161` is the documented undo."""
        self._apply_cascade()
        self.assertEqual(self._delete_type(), "c")

        self._restore_no_action()

        self.assertEqual(self._delete_type(), "a")


class TestAssistantConversationAdminAccess(TestCase):
    """Superuser-only access to transcripts, and the 500 that used to hide behind it.

    `SecureAdmin` scopes a changelist by white label whenever
    `hasattr(self.model, "white_label")` is true — and that is true here even though
    `white_label` is a plain CharField holding a code, because Django gives every
    concrete field a `DeferredAttribute` class descriptor. So the base class took its
    scoping branch and ran `filter(white_label__in=request.user.white_labels.all())`,
    comparing a varchar column against a subquery of integer primary keys. Postgres
    raised `operator does not exist: character varying = bigint`, which is a 500 on
    the changelist for every non-superuser staff member — and, before that, the
    section was listed in the admin nav for them at all, which is the opposite of what
    these PII rows need.
    """

    def setUp(self):
        self.admin = AssistantConversationAdmin(AssistantConversation, AdminSite())
        self.factory = RequestFactory()

        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.conversation = make_conversation(white_label="test")

        self.staff = User.objects.create_user(email_or_cell="tenant-staff@example.com", password="pw")
        self.staff.is_staff = True
        self.staff.save()
        self.staff.white_labels.add(self.white_label)

        self.superuser = User.objects.create_user(email_or_cell="root@example.com", password="pw")
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

    def _request(self, user):
        request = self.factory.get("/admin/screener/assistantconversation/")
        request.user = user
        return request

    def test_tenant_staff_get_an_empty_queryset_rather_than_a_database_error(self):
        """The regression. Evaluating the queryset is the assertion — before the fix
        this raised ProgrammingError instead of returning rows."""
        queryset = self.admin.get_queryset(self._request(self.staff))

        self.assertEqual(list(queryset), [])

    def test_tenant_staff_do_not_see_the_section_in_the_admin_nav(self):
        self.assertFalse(self.admin.has_module_permission(self._request(self.staff)))

    def test_tenant_staff_cannot_view_a_transcript(self):
        request = self._request(self.staff)

        self.assertFalse(self.admin.has_view_permission(request))
        self.assertFalse(self.admin.has_view_permission(request, self.conversation))

    def test_superusers_see_every_conversation(self):
        queryset = self.admin.get_queryset(self._request(self.superuser))

        self.assertEqual([c.pk for c in queryset], [self.conversation.pk])

    def test_superusers_can_view_but_not_modify(self):
        """Read-only in every direction: ai-service is the writer, and editing a
        household's transcript after the fact is not something we should be able to
        do."""
        request = self._request(self.superuser)

        self.assertTrue(self.admin.has_view_permission(request))
        self.assertFalse(self.admin.has_add_permission(request))
        self.assertFalse(self.admin.has_change_permission(request, self.conversation))
        self.assertFalse(self.admin.has_delete_permission(request, self.conversation))
