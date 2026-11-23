"""The Benji SMS tables (MFB-2435): phone, binding, delivery and stranger reply.

What these pin: one active binding per phone and per conversation, the delivery
invariants the webhook and worker will rely on, deletion cascading from a conversation
through everything SMS hangs off it (in the ORM and, with migration 0172, in raw SQL),
and an admin that only superusers can see, nobody can edit, and that never searches by
phone hash.
"""

import importlib
import uuid
from datetime import timedelta

from django.contrib.admin.sites import AdminSite
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.http import HttpRequest
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from authentication.models import User
from screener.admin import (
    AssistantConversationAdmin,
    BenjiSmsBindingAdmin,
    BenjiSmsDeadLetterAdmin,
    BenjiSmsDeliveryAdmin,
    BenjiSmsPhoneAdmin,
    BenjiSmsStrangerReplyAdmin,
    SuperuserReadOnlyAdmin,
)
from screener.models import (
    AssistantChannel,
    AssistantConversation,
    AssistantConversationStatus,
    AssistantMessage,
    BenjiSmsBinding,
    BenjiSmsDeadLetter,
    BenjiSmsDelivery,
    BenjiSmsDeliveryKind,
    BenjiSmsDeliveryStatus,
    BenjiSmsPhone,
    BenjiSmsStrangerReply,
    WhiteLabel,
)
from screener.tests.assistant_helpers import make_conversation, make_message

# Imported by name because the modules start with a digit.
MIGRATION_0163 = importlib.import_module("screener.migrations.0163_assistant_message_db_cascade")
MIGRATION_0172 = importlib.import_module("screener.migrations.0172_benji_sms_db_cascade")

HASH = "a" * 64
OTHER_HASH = "b" * 64
SID = "SM" + "3" * 32

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


def make_phone(phone_hash: str = HASH) -> BenjiSmsPhone:
    return BenjiSmsPhone.objects.create(phone_hash=phone_hash)


def make_binding(white_label: WhiteLabel, phone: BenjiSmsPhone, **overrides: object) -> BenjiSmsBinding:
    if "conversation" not in overrides:
        overrides["conversation"] = make_conversation(white_label=white_label.code, channel=AssistantChannel.SMS)
    defaults = {
        "phone": phone,
        "white_label": white_label,
        "consented_at": timezone.now(),
        "consent_version": "benji.sms.consent-v1",
    }
    return BenjiSmsBinding.objects.create(**{**defaults, **overrides})


def make_delivery(**overrides: object) -> BenjiSmsDelivery:
    defaults = {"kind": BenjiSmsDeliveryKind.FIXED}
    return BenjiSmsDelivery.objects.create(**{**defaults, **overrides})


def make_dead_letter(conversation: AssistantConversation, **overrides: object) -> BenjiSmsDeadLetter:
    defaults = {
        "task_name": "screener.benji_sms_turn",
        "task_id": str(uuid.uuid4()),
        "conversation": conversation,
        "inbound_sid": SID,
        "attempts": 2,
        "error_type": "requests.exceptions.Timeout",
    }
    return BenjiSmsDeadLetter.objects.create(**{**defaults, **overrides})


class TestPhone(TestCase):
    def test_one_row_per_hash(self) -> None:
        make_phone()

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_phone()

    def test_str_carries_no_phone_hash(self) -> None:
        self.assertNotIn(HASH, str(make_phone()))

    def test_a_phone_with_bindings_cannot_be_deleted_before_its_conversations(self) -> None:
        """PROTECT, so a deletion request cannot drop the phone and orphan its texts."""
        phone = make_phone()
        make_binding(make_white_label(), phone)

        with self.assertRaises(ProtectedError):
            phone.delete()


class TestBindingConstraints(TestCase):
    def setUp(self) -> None:
        self.white_label = make_white_label()
        self.phone = make_phone()

    def test_one_active_binding_per_phone(self) -> None:
        make_binding(self.white_label, self.phone)

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_binding(self.white_label, self.phone)

    def test_a_phone_can_hold_closed_and_expired_bindings_beside_an_active_one(self) -> None:
        """Several closed bindings over time is a normal state (decision 3)."""
        make_binding(self.white_label, self.phone, status=AssistantConversationStatus.CLOSED)
        make_binding(self.white_label, self.phone, status=AssistantConversationStatus.EXPIRED)
        make_binding(self.white_label, self.phone, status=AssistantConversationStatus.CLOSED)
        make_binding(self.white_label, self.phone)

        self.assertEqual(self.phone.bindings.count(), 4)

    def test_different_phones_can_each_hold_an_active_binding(self) -> None:
        make_binding(self.white_label, self.phone)
        make_binding(self.white_label, make_phone(OTHER_HASH))

        self.assertEqual(BenjiSmsBinding.objects.filter(status="active").count(), 2)

    def test_two_phones_cannot_both_be_active_on_one_conversation(self) -> None:
        """ai-service keeps one active SMS conversation per screen, so a second phone's
        on-ramp on the same screen would be handed this one. The database refuses."""
        first = make_binding(self.white_label, self.phone)

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_binding(self.white_label, make_phone(OTHER_HASH), conversation=first.conversation)

    def test_a_conversation_never_takes_a_second_binding_even_after_the_first_closes(self) -> None:
        """A conversation belongs to one phone for good, enforced by the database."""
        first = make_binding(self.white_label, self.phone, status=AssistantConversationStatus.CLOSED)

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_binding(self.white_label, make_phone(OTHER_HASH), conversation=first.conversation)

        self.assertEqual(list(BenjiSmsBinding.objects.filter(conversation=first.conversation)), [first])

    def test_status_outside_the_vocabulary_is_rejected(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_binding(self.white_label, self.phone, status="paused")

    def test_a_white_label_with_bindings_cannot_be_deleted(self) -> None:
        make_binding(self.white_label, self.phone)

        with self.assertRaises(ProtectedError):
            self.white_label.delete()

    def test_str_carries_no_phone_hash(self) -> None:
        self.assertNotIn(HASH, str(make_binding(self.white_label, self.phone)))


class TestDeliveryConstraints(TestCase):
    def setUp(self) -> None:
        self.binding = make_binding(make_white_label(), make_phone())
        self.message = make_message(self.binding.conversation, seq=0, role="assistant")

    def test_a_reply_needs_its_message(self) -> None:
        for kind in (BenjiSmsDeliveryKind.REPLY, BenjiSmsDeliveryKind.REMAINDER):
            with self.subTest(kind=kind), self.assertRaises(IntegrityError), transaction.atomic():
                make_delivery(kind=kind, binding=self.binding)

    def test_a_conversation_text_needs_its_binding(self) -> None:
        """Every send checks the phone's revocation through the binding."""
        for kind in (BenjiSmsDeliveryKind.REPLY, BenjiSmsDeliveryKind.REMAINDER, BenjiSmsDeliveryKind.DISCLOSURE):
            with self.subTest(kind=kind), self.assertRaises(IntegrityError), transaction.atomic():
                make_delivery(kind=kind, message=self.message)

    def test_a_reply_with_its_message_and_binding_is_accepted(self) -> None:
        delivery = make_delivery(kind=BenjiSmsDeliveryKind.REPLY, message=self.message, binding=self.binding)

        self.assertEqual(delivery.message, self.message)

    def test_onramp_and_fixed_texts_need_neither(self) -> None:
        """A shared-phone on-ramp opens no binding; a stranger has none."""
        for kind in (BenjiSmsDeliveryKind.ONRAMP, BenjiSmsDeliveryKind.FIXED):
            with self.subTest(kind=kind):
                make_delivery(kind=kind)

    def test_kind_outside_the_vocabulary_is_rejected(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_delivery(kind="survey", binding=self.binding)

    def test_outbound_sid_is_unique(self) -> None:
        """The status callback finds its row by outbound SID."""
        make_delivery(outbound_sid=SID)

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_delivery(outbound_sid=SID)

    def test_unsent_rows_do_not_collide_on_a_missing_outbound_sid(self) -> None:
        make_delivery()
        make_delivery()

        self.assertEqual(BenjiSmsDelivery.objects.filter(outbound_sid__isnull=True).count(), 2)

    def test_one_inbound_can_produce_the_disclosure_and_the_reply(self) -> None:
        inbound = "SM" + "2" * 32
        make_delivery(kind=BenjiSmsDeliveryKind.DISCLOSURE, binding=self.binding, inbound_sid=inbound)
        make_delivery(kind=BenjiSmsDeliveryKind.REPLY, binding=self.binding, message=self.message, inbound_sid=inbound)

        self.assertEqual(BenjiSmsDelivery.objects.filter(inbound_sid=inbound).count(), 2)

    def test_every_twilio_status_fits_the_column(self) -> None:
        """`partially_delivered` is 19 characters; a status callback must never fail on width."""
        delivery = make_delivery()
        for status in BenjiSmsDeliveryStatus.values:
            with self.subTest(status=status):
                BenjiSmsDelivery.objects.filter(pk=delivery.pk).update(delivery_status=status)
                delivery.refresh_from_db()
                self.assertEqual(delivery.delivery_status, status)


class TestStrangerReply(TestCase):
    def test_one_row_per_phone(self) -> None:
        """What makes "once a day" race-free: a second insert for the hash fails."""
        BenjiSmsStrangerReply.objects.create(phone_hash=HASH)

        with self.assertRaises(IntegrityError), transaction.atomic():
            BenjiSmsStrangerReply.objects.create(phone_hash=HASH)

    def test_str_carries_no_phone_hash(self) -> None:
        self.assertNotIn(HASH, str(BenjiSmsStrangerReply.objects.create(phone_hash=HASH)))


class TestOrmCascade(TestCase):
    """Deleting a conversation is how a deletion request is served (privacy §6)."""

    def setUp(self) -> None:
        self.phone = make_phone()
        self.binding = make_binding(make_white_label(), self.phone)
        self.conversation = self.binding.conversation
        self.message = make_message(self.conversation, seq=0, role="assistant")
        make_delivery(kind=BenjiSmsDeliveryKind.REPLY, message=self.message, binding=self.binding)
        make_delivery(kind=BenjiSmsDeliveryKind.DISCLOSURE, binding=self.binding)

    def test_deleting_the_conversation_removes_its_binding_and_every_delivery(self) -> None:
        self.conversation.delete()

        self.assertFalse(BenjiSmsBinding.objects.exists())
        self.assertFalse(BenjiSmsDelivery.objects.exists())

    def test_then_the_phone_row_can_go(self) -> None:
        self.conversation.delete()

        self.phone.delete()

        self.assertFalse(BenjiSmsPhone.objects.exists())

    def test_deleting_a_binding_leaves_the_conversation(self) -> None:
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

    def setUp(self) -> None:
        self.addCleanup(self._restore_no_action)

    def _restore_no_action(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0172._DROP_DB_CASCADE)
            cursor.execute(MIGRATION_0163._DROP_DB_CASCADE)

    def _apply_cascades(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0163._ADD_DB_CASCADE)
            cursor.execute(MIGRATION_0172._ADD_DB_CASCADE)

    def _delete_types(self) -> dict[str, str]:
        """`confdeltype` per foreign-key column: 'a' = no action, 'c' = cascade."""
        with connection.cursor() as cursor:
            cursor.execute(SMS_FK_DELETE_TYPES_SQL)
            return dict(cursor.fetchall())

    def _seed(self) -> AssistantConversation:
        binding = make_binding(make_white_label(), make_phone())
        message = make_message(binding.conversation, seq=0, role="assistant")
        make_delivery(kind=BenjiSmsDeliveryKind.REPLY, message=message, binding=binding)
        make_delivery(kind=BenjiSmsDeliveryKind.DISCLOSURE, binding=binding)
        return binding.conversation

    def _raw_delete(self, conversation_id: uuid.UUID) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM screener_assistantconversation WHERE conversation_id = %s",
                [str(conversation_id)],
            )

    def test_the_test_database_starts_without_the_cascade(self) -> None:
        """Guards against this class becoming vacuous if `--nomigrations` goes away."""
        self.assertEqual(set(self._delete_types().values()), {"a"})

    def test_migration_sql_cascades_the_three_sms_foreign_keys_and_nothing_else(self) -> None:
        self._apply_cascades()

        self.assertEqual(
            self._delete_types(),
            {
                "conversation_id": "c",
                "message_id": "c",
                "binding_id": "c",
                "white_label_id": "a",
                "phone_id": "a",
            },
        )

    def test_a_raw_delete_of_the_conversation_removes_everything_but_the_phone(self) -> None:
        """The deletion-request path: one statement, then the phone row."""
        self._apply_cascades()
        conversation = self._seed()

        self._raw_delete(conversation.pk)

        self.assertFalse(AssistantMessage.objects.exists())
        self.assertFalse(BenjiSmsBinding.objects.exists())
        self.assertFalse(BenjiSmsDelivery.objects.exists())
        self.assertEqual(BenjiSmsPhone.objects.count(), 1)

    def test_a_raw_delete_fails_without_the_migration(self) -> None:
        """0172 is load-bearing: with only 0163, the binding blocks the delete."""
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0163._ADD_DB_CASCADE)
        conversation = self._seed()

        with self.assertRaises(IntegrityError):
            self._raw_delete(conversation.pk)

    def test_reverse_sql_restores_no_action(self) -> None:
        self._apply_cascades()

        with connection.cursor() as cursor:
            cursor.execute(MIGRATION_0172._DROP_DB_CASCADE)

        self.assertEqual(set(self._delete_types().values()), {"a"})


class TestSmsAdminAccess(TestCase):
    """Superusers only, read-only, for every SMS table (privacy companion §11).

    `BenjiSmsBinding` has a real `white_label` FK, so SecureAdmin alone would show a
    white label's bindings to its staff. These tests pin that it does not.
    """

    ADMINS = (
        (BenjiSmsPhoneAdmin, BenjiSmsPhone),
        (BenjiSmsBindingAdmin, BenjiSmsBinding),
        (BenjiSmsDeliveryAdmin, BenjiSmsDelivery),
        (BenjiSmsStrangerReplyAdmin, BenjiSmsStrangerReply),
        (BenjiSmsDeadLetterAdmin, BenjiSmsDeadLetter),
    )

    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.white_label = make_white_label()
        self.phone = make_phone()
        self.binding = make_binding(self.white_label, self.phone)
        self.delivery = make_delivery(
            kind=BenjiSmsDeliveryKind.DISCLOSURE, binding=self.binding, inbound_sid="SM" + "4" * 32, outbound_sid=SID
        )
        self.stranger = BenjiSmsStrangerReply.objects.create(phone_hash=OTHER_HASH)
        self.dead_letter = make_dead_letter(self.binding.conversation)
        self.rows = {
            BenjiSmsPhone: self.phone,
            BenjiSmsBinding: self.binding,
            BenjiSmsDelivery: self.delivery,
            BenjiSmsStrangerReply: self.stranger,
            BenjiSmsDeadLetter: self.dead_letter,
        }

        self.staff = User.objects.create_user(email_or_cell="tenant-staff@example.com", password="pw")
        self.staff.is_staff = True
        self.staff.save()
        self.staff.white_labels.add(self.white_label)

        self.superuser = User.objects.create_user(email_or_cell="root@example.com", password="pw")
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

    def _request(self, user: User) -> HttpRequest:
        request = self.factory.get("/admin/")
        request.user = user
        return request

    def _search(self, admin_class: type, model: type, term: str) -> list:
        model_admin = admin_class(model, AdminSite())
        request = self._request(self.superuser)
        results, _ = model_admin.get_search_results(request, model_admin.get_queryset(request), term)
        return [row.pk for row in results]

    def test_tenant_staff_see_nothing_even_for_their_own_white_label(self) -> None:
        request = self._request(self.staff)
        for admin_class, model in self.ADMINS:
            with self.subTest(model=model.__name__):
                model_admin = admin_class(model, AdminSite())
                self.assertEqual(list(model_admin.get_queryset(request)), [])
                self.assertFalse(model_admin.has_module_permission(request))
                self.assertFalse(model_admin.has_view_permission(request))
                self.assertFalse(model_admin.has_view_permission(request, self.rows[model]))

    def test_superusers_can_view_but_not_modify(self) -> None:
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

    def test_the_transcript_admin_shares_the_same_base(self) -> None:
        self.assertTrue(issubclass(AssistantConversationAdmin, SuperuserReadOnlyAdmin))

    def test_no_admin_searches_by_phone_hash(self) -> None:
        """A search term lands in the URL, the router logs and Sentry's request data."""
        for admin_class, _ in self.ADMINS:
            with self.subTest(admin=admin_class.__name__):
                self.assertFalse(any("phone_hash" in field for field in admin_class.search_fields))
        self.assertEqual(self._search(BenjiSmsBindingAdmin, BenjiSmsBinding, HASH), [])

    def test_bindings_are_found_by_exact_screen_or_conversation(self) -> None:
        conversation = self.binding.conversation
        for term in (str(conversation.screen_uuid), str(conversation.conversation_id)):
            with self.subTest(term=term):
                self.assertEqual(self._search(BenjiSmsBindingAdmin, BenjiSmsBinding, term), [self.binding.pk])

    def test_binding_search_never_errors_on_a_value_that_is_not_a_uuid(self) -> None:
        for term in (SID, "not a uuid", str(self.binding.conversation.screen_uuid)[:8]):
            with self.subTest(term=term):
                self.assertEqual(self._search(BenjiSmsBindingAdmin, BenjiSmsBinding, term), [])

    def test_deliveries_are_found_by_exact_inbound_or_outbound_sid(self) -> None:
        for term in (SID, "SM" + "4" * 32):
            with self.subTest(term=term):
                self.assertEqual(self._search(BenjiSmsDeliveryAdmin, BenjiSmsDelivery, term), [self.delivery.pk])
        self.assertEqual(self._search(BenjiSmsDeliveryAdmin, BenjiSmsDelivery, SID[:10]), [])

    def test_an_empty_search_lists_everything(self) -> None:
        self.assertEqual(self._search(BenjiSmsDeliveryAdmin, BenjiSmsDelivery, "  "), [self.delivery.pk])


# The manifest storage needs collectstatic; authentication/tests.py does the same.
@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class TestSmsAdminPagesRender(TestCase):
    """The changelist, a search and the detail page each load for a superuser."""

    def setUp(self) -> None:
        self.binding = make_binding(make_white_label(), make_phone())
        message = make_message(self.binding.conversation, seq=0, role="assistant")
        self.delivery = make_delivery(
            kind=BenjiSmsDeliveryKind.REPLY, message=message, binding=self.binding, outbound_sid=SID
        )
        self.stranger = BenjiSmsStrangerReply.objects.create(phone_hash=OTHER_HASH)
        self.dead_letter = make_dead_letter(self.binding.conversation)
        superuser = User.objects.create_user(email_or_cell="root@example.com", password="pw")
        superuser.is_staff = True
        superuser.is_superuser = True
        superuser.save()
        self.client.force_login(superuser)

    def test_every_page_loads(self) -> None:
        rows = {
            "benjismsphone": self.binding.phone,
            "benjismsbinding": self.binding,
            "benjismsdelivery": self.delivery,
            "benjismsstrangerreply": self.stranger,
            "benjismsdeadletter": self.dead_letter,
        }
        for name, row in rows.items():
            base = f"/admin/screener/{name}/"
            for url in (base, f"{base}?q={SID}", f"{base}{row.pk}/change/"):
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_the_phone_hash_is_not_in_any_changelist(self) -> None:
        for name in ("benjismsphone", "benjismsbinding", "benjismsstrangerreply"):
            with self.subTest(name=name):
                body = self.client.get(f"/admin/screener/{name}/").content.decode()
                self.assertNotIn(HASH, body)
                self.assertNotIn(OTHER_HASH, body)


KEY_SETTINGS = {"BENJI_SMS_HASH_KEY": "k" * 64}
NUMBER = "+13035550100"


class TestBindingOnlyOnSmsConversations(TestCase):
    def test_a_binding_on_a_web_conversation_is_refused(self) -> None:
        """Texts would otherwise land in the transcript the browser widget shows."""
        web = make_conversation(white_label="test_sms", channel=AssistantChannel.WEB)

        with self.assertRaises(ValueError):
            make_binding(make_white_label(), make_phone(), conversation=web)

        self.assertFalse(BenjiSmsBinding.objects.exists())

    def test_saving_other_fields_of_an_existing_binding_is_allowed(self) -> None:
        binding = make_binding(make_white_label(), make_phone())
        binding.last_inbound_at = timezone.now()

        binding.save()

        binding.refresh_from_db()
        self.assertIsNotNone(binding.last_inbound_at)

    def test_an_existing_binding_cannot_be_moved_to_a_web_conversation(self) -> None:
        binding = make_binding(make_white_label(), make_phone())
        original = binding.conversation_id
        binding.conversation = make_conversation(white_label="test_sms", channel=AssistantChannel.WEB)

        with self.assertRaises(ValueError):
            binding.save()

        self.assertEqual(BenjiSmsBinding.objects.get(pk=binding.pk).conversation_id, original)

    def test_an_existing_binding_cannot_change_conversation_or_phone(self) -> None:
        white_label = make_white_label()
        binding = make_binding(white_label, make_phone())
        moves = {
            "conversation": make_conversation(white_label=white_label.code, channel=AssistantChannel.SMS),
            "phone": make_phone(OTHER_HASH),
        }
        for field, value in moves.items():
            with self.subTest(field=field):
                fresh = BenjiSmsBinding.objects.get(pk=binding.pk)
                setattr(fresh, field, value)
                with self.assertRaises(ValueError):
                    fresh.save()


class TestBindingEnd(TestCase):
    def setUp(self) -> None:
        self.phone = make_phone()
        self.binding = make_binding(make_white_label(), self.phone)

    def test_closing_moves_the_binding_and_its_conversation_together(self) -> None:
        for status in (AssistantConversationStatus.CLOSED, AssistantConversationStatus.EXPIRED):
            with self.subTest(status=status):
                self.binding.end(status)

                self.binding.refresh_from_db()
                self.binding.conversation.refresh_from_db()
                self.assertEqual(self.binding.status, status)
                self.assertEqual(self.binding.conversation.status, status)

    def test_only_an_ending_status_is_accepted(self) -> None:
        with self.assertRaises(ValueError):
            self.binding.end(AssistantConversationStatus.ACTIVE)

        self.binding.refresh_from_db()
        self.assertEqual(self.binding.status, AssistantConversationStatus.ACTIVE)

    def test_an_ended_binding_frees_the_phone_for_its_next_on_ramp(self) -> None:
        self.binding.end(AssistantConversationStatus.CLOSED)

        make_binding(make_white_label("test_sms_2"), self.phone)

        self.assertEqual(self.phone.bindings.filter(status="active").count(), 1)


@override_settings(**KEY_SETTINGS)
class TestLookupByNumber(TestCase):
    def test_every_spelling_finds_the_phone(self) -> None:
        from integrations.services.communications.benji_sms_hash import phone_hash

        phone = make_phone(phone_hash(NUMBER))
        for spelling in (NUMBER, "(303) 555-0100", "303.555.0100"):
            with self.subTest(spelling=spelling):
                self.assertEqual(BenjiSmsPhone.objects.for_number(spelling), phone)

    def test_an_unknown_number_finds_nothing(self) -> None:
        self.assertIsNone(BenjiSmsPhone.objects.for_number(NUMBER))
        self.assertFalse(BenjiSmsStrangerReply.objects.for_number(NUMBER).exists())

    def test_finds_the_stranger_row(self) -> None:
        from integrations.services.communications.benji_sms_hash import phone_hash

        BenjiSmsStrangerReply.objects.create(phone_hash=phone_hash(NUMBER))

        self.assertEqual(BenjiSmsStrangerReply.objects.for_number("303-555-0100").count(), 1)


class TestDeleteWithConversations(TestCase):
    """A deletion request: everything SMS for the phone, nothing else."""

    def setUp(self) -> None:
        self.white_label = make_white_label()
        self.phone = make_phone()
        self.closed = make_binding(self.white_label, self.phone, status=AssistantConversationStatus.CLOSED)
        self.active = make_binding(self.white_label, self.phone)
        message = make_message(self.active.conversation, seq=0, role="assistant")
        make_delivery(kind=BenjiSmsDeliveryKind.REPLY, message=message, binding=self.active)
        BenjiSmsStrangerReply.objects.create(phone_hash=HASH)
        # The web widget's conversation on the same screen, and another phone entirely.
        self.web = make_conversation(
            white_label=self.white_label.code,
            channel=AssistantChannel.WEB,
            screen_uuid=self.active.conversation.screen_uuid,
        )
        self.other = make_binding(self.white_label, make_phone(OTHER_HASH))

    def test_deletes_the_phones_sms_conversations_and_everything_on_them(self) -> None:
        deleted = self.phone.delete_with_conversations()

        self.assertEqual(deleted, 2)
        self.assertFalse(BenjiSmsPhone.objects.filter(pk=self.phone.pk).exists())
        self.assertFalse(BenjiSmsStrangerReply.objects.filter(phone_hash=HASH).exists())
        self.assertFalse(
            AssistantConversation.objects.filter(
                pk__in=[self.closed.conversation_id, self.active.conversation_id]
            ).exists()
        )
        self.assertFalse(BenjiSmsDelivery.objects.exists())
        self.assertFalse(AssistantMessage.objects.exists())

    def test_leaves_the_web_conversation_and_other_phones_alone(self) -> None:
        self.phone.delete_with_conversations()

        self.assertTrue(AssistantConversation.objects.filter(pk=self.web.pk).exists())
        self.assertTrue(BenjiSmsBinding.objects.filter(pk=self.other.pk).exists())

    def test_another_phone_cannot_bind_a_conversation_this_phone_closed(self) -> None:
        """Otherwise deleting this phone's data would delete the other phone's
        transcript with it (the conversation cascades to every binding on it)."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_binding(self.white_label, self.other.phone, conversation=self.closed.conversation)

        self.phone.delete_with_conversations()

        self.assertTrue(BenjiSmsBinding.objects.filter(pk=self.other.pk).exists())

    def test_rolls_back_rather_than_delete_a_web_transcript(self) -> None:
        """A binding forced onto the web conversation (bypassing save) survives the SMS
        delete, PROTECT refuses the phone row, and nothing at all is deleted."""
        BenjiSmsBinding.objects.filter(pk=self.closed.pk).update(conversation=self.web)

        with self.assertRaises(ProtectedError):
            self.phone.delete_with_conversations()

        self.assertTrue(AssistantConversation.objects.filter(pk=self.web.pk).exists())
        self.assertTrue(AssistantConversation.objects.filter(pk=self.active.conversation_id).exists())
        self.assertTrue(BenjiSmsPhone.objects.filter(pk=self.phone.pk).exists())


class TestPurgeExpired(TestCase):
    def test_purges_stranger_rows_and_unbound_deliveries_older_than_a_day(self) -> None:
        now = timezone.now()
        old, recent = now - timedelta(days=1, minutes=1), now - timedelta(hours=23)
        binding = make_binding(make_white_label(), make_phone())
        BenjiSmsStrangerReply.objects.create(phone_hash=HASH, replied_at=old)
        kept_stranger = BenjiSmsStrangerReply.objects.create(phone_hash=OTHER_HASH, replied_at=recent)
        make_delivery(kind=BenjiSmsDeliveryKind.FIXED, created_at=old)
        kept_unbound = make_delivery(kind=BenjiSmsDeliveryKind.FIXED, created_at=recent)
        kept_bound = make_delivery(kind=BenjiSmsDeliveryKind.DISCLOSURE, binding=binding, created_at=old)

        counts = BenjiSmsStrangerReply.objects.purge_expired(now=now)

        self.assertEqual(counts, (1, 1))
        self.assertEqual(list(BenjiSmsStrangerReply.objects.all()), [kept_stranger])
        self.assertEqual(set(BenjiSmsDelivery.objects.values_list("pk", flat=True)), {kept_unbound.pk, kept_bound.pk})


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class TestBindingChangelistQueries(TestCase):
    def setUp(self) -> None:
        self.white_label = make_white_label()
        superuser = User.objects.create_user(email_or_cell="root@example.com", password="pw")
        superuser.is_staff = True
        superuser.is_superuser = True
        superuser.save()
        self.client.force_login(superuser)

    def _queries_for_changelist(self) -> int:
        from django.db import connection as conn
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(conn) as captured:
            self.assertEqual(self.client.get("/admin/screener/benjismsbinding/").status_code, 200)
        return len(captured)

    def test_query_count_does_not_grow_with_rows(self) -> None:
        make_binding(self.white_label, make_phone())
        one = self._queries_for_changelist()
        make_binding(self.white_label, make_phone(OTHER_HASH))
        make_binding(self.white_label, make_phone("c" * 64))

        self.assertEqual(self._queries_for_changelist(), one)
