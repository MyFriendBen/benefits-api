"""The Benji SMS tables (MFB-2435): binding, delivery and stranger reply.

What these pin: one active binding per phone, the delivery invariants the webhook and
worker will rely on, deletion cascading from a conversation through everything SMS
hangs off it (in the ORM and, with migration 0172, in raw SQL), and an admin that only
superusers can see and nobody can edit.
"""

import importlib

from django.contrib.admin.sites import AdminSite
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.utils import timezone

from authentication.models import User
from screener.admin import BenjiSmsBindingAdmin, BenjiSmsDeliveryAdmin, BenjiSmsStrangerReplyAdmin
from screener.models import (
    AssistantChannel,
    AssistantConversation,
    AssistantMessage,
    BenjiSmsBinding,
    BenjiSmsBindingStatus,
    BenjiSmsDelivery,
    BenjiSmsDeliveryKind,
    BenjiSmsStrangerReply,
    WhiteLabel,
)
from screener.tests.test_assistant_conversation_store import make_conversation, make_message

# Imported by name because the modules start with a digit.
MIGRATION_0163 = importlib.import_module("screener.migrations.0163_assistant_message_db_cascade")
MIGRATION_0172 = importlib.import_module("screener.migrations.0172_benji_sms_db_cascade")

HASH = "a" * 64
OTHER_HASH = "b" * 64

# Kept as a named constant: see FK_DELETE_TYPE_SQL in test_assistant_conversation_store.
SMS_FK_DELETE_TYPES_SQL = """
SELECT a.attname, c.confdeltype
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
WHERE c.conrelid IN ('screener_benjismsbinding'::regclass, 'screener_benjismsdelivery'::regclass)
  AND c.contype = 'f'
"""


def make_white_label(code: str = "test_sms") -> WhiteLabel:
    return WhiteLabel.objects.create(name="Test", code=code, state_code="TS")


def make_binding(white_label: WhiteLabel, **overrides) -> BenjiSmsBinding:
    if "conversation" not in overrides:
        overrides["conversation"] = make_conversation(white_label=white_label.code, channel=AssistantChannel.SMS)
    defaults = {
        "phone_hash": HASH,
        "screen_uuid": overrides["conversation"].screen_uuid,
        "white_label": white_label,
        "consented_at": timezone.now(),
        "consent_version": "benji.sms.consent-v1",
    }
    return BenjiSmsBinding.objects.create(**{**defaults, **overrides})


def make_delivery(**overrides) -> BenjiSmsDelivery:
    defaults = {"kind": BenjiSmsDeliveryKind.FIXED}
    return BenjiSmsDelivery.objects.create(**{**defaults, **overrides})


class TestBindingConstraints(TestCase):
    def setUp(self):
        self.white_label = make_white_label()

    def test_one_active_binding_per_phone(self):
        make_binding(self.white_label)

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_binding(self.white_label)

    def test_a_phone_can_hold_closed_and_expired_bindings_beside_an_active_one(self):
        """Several closed bindings over time is a normal state (decision 3)."""
        make_binding(self.white_label, status=BenjiSmsBindingStatus.CLOSED)
        make_binding(self.white_label, status=BenjiSmsBindingStatus.EXPIRED)
        make_binding(self.white_label, status=BenjiSmsBindingStatus.CLOSED)
        make_binding(self.white_label)

        self.assertEqual(BenjiSmsBinding.objects.filter(phone_hash=HASH).count(), 4)

    def test_different_phones_can_each_hold_an_active_binding(self):
        make_binding(self.white_label)
        make_binding(self.white_label, phone_hash=OTHER_HASH)

        self.assertEqual(BenjiSmsBinding.objects.filter(status="active").count(), 2)

    def test_status_outside_the_vocabulary_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_binding(self.white_label, status="paused")

    def test_a_white_label_with_bindings_cannot_be_deleted(self):
        make_binding(self.white_label)

        with self.assertRaises(ProtectedError):
            self.white_label.delete()

    def test_str_carries_no_phone_hash(self):
        binding = make_binding(self.white_label)

        self.assertNotIn(HASH, str(binding))


class TestDeliveryConstraints(TestCase):
    def setUp(self):
        self.binding = make_binding(make_white_label())
        self.message = make_message(self.binding.conversation, seq=0, role="assistant")

    def test_a_reply_needs_its_message(self):
        for kind in (BenjiSmsDeliveryKind.REPLY, BenjiSmsDeliveryKind.REMAINDER):
            with self.subTest(kind=kind), self.assertRaises(IntegrityError), transaction.atomic():
                make_delivery(kind=kind, binding=self.binding)

    def test_a_reply_with_its_message_is_accepted(self):
        delivery = make_delivery(kind=BenjiSmsDeliveryKind.REPLY, message=self.message, binding=self.binding)

        self.assertEqual(delivery.message, self.message)

    def test_texts_no_model_wrote_need_no_message(self):
        for kind in (BenjiSmsDeliveryKind.ONRAMP, BenjiSmsDeliveryKind.DISCLOSURE, BenjiSmsDeliveryKind.FIXED):
            with self.subTest(kind=kind):
                make_delivery(kind=kind, binding=self.binding)

    def test_a_stranger_reply_needs_no_binding(self):
        make_delivery(kind=BenjiSmsDeliveryKind.FIXED, inbound_sid="SM" + "0" * 32)

    def test_kind_outside_the_vocabulary_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_delivery(kind="survey", binding=self.binding)

    def test_outbound_sid_is_unique(self):
        """The status callback finds its row by outbound SID."""
        make_delivery(outbound_sid="SM" + "1" * 32)

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_delivery(outbound_sid="SM" + "1" * 32)

    def test_unsent_rows_do_not_collide_on_a_missing_outbound_sid(self):
        make_delivery()
        make_delivery()

        self.assertEqual(BenjiSmsDelivery.objects.filter(outbound_sid__isnull=True).count(), 2)

    def test_one_inbound_can_produce_the_disclosure_and_the_reply(self):
        inbound = "SM" + "2" * 32
        make_delivery(kind=BenjiSmsDeliveryKind.DISCLOSURE, binding=self.binding, inbound_sid=inbound)
        make_delivery(kind=BenjiSmsDeliveryKind.REPLY, binding=self.binding, message=self.message, inbound_sid=inbound)

        self.assertEqual(BenjiSmsDelivery.objects.filter(inbound_sid=inbound).count(), 2)


class TestStrangerReply(TestCase):
    def test_one_row_per_phone(self):
        """What makes "once a day" race-free: a second insert for the hash fails."""
        BenjiSmsStrangerReply.objects.create(phone_hash=HASH)

        with self.assertRaises(IntegrityError), transaction.atomic():
            BenjiSmsStrangerReply.objects.create(phone_hash=HASH)

    def test_str_carries_no_phone_hash(self):
        self.assertNotIn(HASH, str(BenjiSmsStrangerReply.objects.create(phone_hash=HASH)))


class TestOrmCascade(TestCase):
    """Deleting a conversation is how a deletion request is served (privacy §6)."""

    def setUp(self):
        self.binding = make_binding(make_white_label())
        self.conversation = self.binding.conversation
        self.message = make_message(self.conversation, seq=0, role="assistant")
        make_delivery(kind=BenjiSmsDeliveryKind.REPLY, message=self.message, binding=self.binding)
        make_delivery(kind=BenjiSmsDeliveryKind.DISCLOSURE, binding=self.binding)

    def test_deleting_the_conversation_removes_its_binding_and_every_delivery(self):
        self.conversation.delete()

        self.assertFalse(BenjiSmsBinding.objects.exists())
        self.assertFalse(BenjiSmsDelivery.objects.exists())

    def test_deleting_a_binding_leaves_the_conversation(self):
        self.binding.delete()

        self.assertTrue(AssistantConversation.objects.filter(pk=self.conversation.pk).exists())
        self.assertTrue(AssistantMessage.objects.filter(pk=self.message.pk).exists())


class TestDatabaseLevelCascade(TransactionTestCase):
    """Migration 0172's SQL, run for real, as TestDatabaseLevelCascade does for 0163.

    pytest runs with `--nomigrations`, so the test schema has no database-level
    cascade until the migrations' SQL is applied here. Autocommit (TransactionTestCase)
    because Postgres refuses ALTER TABLE with pending deferred-FK trigger events, and
    because deferred constraints inside a test transaction fire at commit, not at the
    statement as in production.
    """

    def setUp(self):
        self.addCleanup(self._restore_no_action)

    def _restore_no_action(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0172._DROP_DB_CASCADE)
            cursor.execute(MIGRATION_0163._DROP_DB_CASCADE)

    def _apply_cascades(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0163._ADD_DB_CASCADE)
            cursor.execute(MIGRATION_0172._ADD_DB_CASCADE)

    def _delete_types(self) -> dict:
        """`confdeltype` per foreign-key column: 'a' = no action, 'c' = cascade."""
        with connection.cursor() as cursor:
            cursor.execute(SMS_FK_DELETE_TYPES_SQL)
            return dict(cursor.fetchall())

    def _seed(self) -> AssistantConversation:
        binding = make_binding(make_white_label())
        message = make_message(binding.conversation, seq=0, role="assistant")
        make_delivery(kind=BenjiSmsDeliveryKind.REPLY, message=message, binding=binding)
        make_delivery(kind=BenjiSmsDeliveryKind.DISCLOSURE, binding=binding)
        return binding.conversation

    def _raw_delete(self, conversation_id) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM screener_assistantconversation WHERE conversation_id = %s",
                [str(conversation_id)],
            )

    def test_the_test_database_starts_without_the_cascade(self):
        """Guards against this class becoming vacuous if `--nomigrations` goes away."""
        self.assertEqual(set(self._delete_types().values()), {"a"})

    def test_migration_sql_cascades_the_three_sms_foreign_keys_and_not_the_white_label(self):
        self._apply_cascades()

        self.assertEqual(
            self._delete_types(),
            {"conversation_id": "c", "message_id": "c", "binding_id": "c", "white_label_id": "a"},
        )

    def test_a_raw_delete_of_the_conversation_removes_everything_sms(self):
        """The deletion-request path: one statement, nothing left behind."""
        self._apply_cascades()
        conversation = self._seed()

        self._raw_delete(conversation.pk)

        self.assertFalse(AssistantMessage.objects.exists())
        self.assertFalse(BenjiSmsBinding.objects.exists())
        self.assertFalse(BenjiSmsDelivery.objects.exists())

    def test_a_raw_delete_fails_without_the_migration(self):
        """0172 is load-bearing: with only 0163, the binding blocks the delete."""
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0163._ADD_DB_CASCADE)
        conversation = self._seed()

        with self.assertRaises(IntegrityError):
            self._raw_delete(conversation.pk)

    def test_reverse_sql_restores_no_action(self):
        self._apply_cascades()

        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0172._DROP_DB_CASCADE)

        self.assertEqual(set(self._delete_types().values()), {"a"})


class TestSmsAdminAccess(TestCase):
    """Superusers only, read-only, for all three tables (privacy companion §11).

    `BenjiSmsBinding` has a real `white_label` FK, so SecureAdmin alone would show a
    white label's bindings to its staff. These tests pin that it does not.
    """

    ADMINS = (
        (BenjiSmsBindingAdmin, BenjiSmsBinding),
        (BenjiSmsDeliveryAdmin, BenjiSmsDelivery),
        (BenjiSmsStrangerReplyAdmin, BenjiSmsStrangerReply),
    )

    def setUp(self):
        self.factory = RequestFactory()
        self.white_label = make_white_label()
        self.binding = make_binding(self.white_label)
        self.delivery = make_delivery(binding=self.binding, outbound_sid="SM" + "3" * 32)
        self.stranger = BenjiSmsStrangerReply.objects.create(phone_hash=OTHER_HASH)
        self.rows = {
            BenjiSmsBinding: self.binding,
            BenjiSmsDelivery: self.delivery,
            BenjiSmsStrangerReply: self.stranger,
        }

        self.staff = User.objects.create_user(email_or_cell="tenant-staff@example.com", password="pw")
        self.staff.is_staff = True
        self.staff.save()
        self.staff.white_labels.add(self.white_label)

        self.superuser = User.objects.create_user(email_or_cell="root@example.com", password="pw")
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

    def _request(self, user, query: str = ""):
        request = self.factory.get("/admin/", {"q": query} if query else {})
        request.user = user
        return request

    def test_tenant_staff_see_nothing_even_for_their_own_white_label(self):
        request = self._request(self.staff)
        for admin_class, model in self.ADMINS:
            with self.subTest(model=model.__name__):
                model_admin = admin_class(model, AdminSite())
                self.assertEqual(list(model_admin.get_queryset(request)), [])
                self.assertFalse(model_admin.has_module_permission(request))
                self.assertFalse(model_admin.has_view_permission(request))
                self.assertFalse(model_admin.has_view_permission(request, self.rows[model]))

    def test_superusers_can_view_but_not_modify(self):
        request = self._request(self.superuser)
        for admin_class, model in self.ADMINS:
            with self.subTest(model=model.__name__):
                model_admin = admin_class(model, AdminSite())
                row = self.rows[model]
                self.assertEqual([r.pk for r in model_admin.get_queryset(request)], [row.pk])
                self.assertTrue(model_admin.has_view_permission(request, row))
                self.assertFalse(model_admin.has_add_permission(request))
                self.assertFalse(model_admin.has_change_permission(request, row))
                self.assertFalse(model_admin.has_delete_permission(request, row))

    def test_search_by_hash_finds_the_binding(self):
        model_admin = BenjiSmsBindingAdmin(BenjiSmsBinding, AdminSite())
        request = self._request(self.superuser, HASH)

        results, _ = model_admin.get_search_results(request, model_admin.get_queryset(request), HASH)

        self.assertEqual([b.pk for b in results], [self.binding.pk])

    def test_search_never_errors_on_a_value_that_is_not_a_uuid(self):
        """A hash or SID pasted into the binding search must not 500 on the uuid fields."""
        model_admin = BenjiSmsBindingAdmin(BenjiSmsBinding, AdminSite())
        request = self._request(self.superuser)

        for query in (OTHER_HASH, "SM" + "3" * 32, "not a uuid"):
            with self.subTest(query=query):
                results, _ = model_admin.get_search_results(request, model_admin.get_queryset(request), query)
                self.assertEqual(list(results), [])

    def test_search_by_outbound_sid_finds_the_delivery(self):
        model_admin = BenjiSmsDeliveryAdmin(BenjiSmsDelivery, AdminSite())
        request = self._request(self.superuser)

        results, _ = model_admin.get_search_results(request, model_admin.get_queryset(request), "SM" + "3" * 32)

        self.assertEqual([d.pk for d in results], [self.delivery.pk])
