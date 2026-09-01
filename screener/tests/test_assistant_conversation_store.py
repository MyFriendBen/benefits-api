"""Tests for the Benji conversation tables.

These tables are unusual: Django owns the schema, mfb-ai-service is the runtime
writer (see screener/models.AssistantConversation). So the constraints are the
contract between the two repos, and these tests are what pin them. If a constraint
here is relaxed, ai-service's Postgres store loses a guarantee it relies on.
"""

import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from screener.models import AssistantConversation, AssistantMessage


def make_conversation(**overrides) -> AssistantConversation:
    defaults = {
        "conversation_id": uuid.uuid4(),
        "screen_uuid": uuid.uuid4(),
        "white_label": "co",
        "locale": "en-US",
        "mode": "live",
        "prompt_version": "test-1",
        "context": {"household": {"size": 3}, "eligible_programs": []},
    }
    return AssistantConversation.objects.create(**{**defaults, **overrides})


def make_message(conversation: AssistantConversation, seq: int, **overrides) -> AssistantMessage:
    defaults = {
        "message_id": uuid.uuid4(),
        "conversation": conversation,
        "seq": seq,
        "role": "user",
        "text": "hello",
    }
    return AssistantMessage.objects.create(**{**defaults, **overrides})


class TestAssistantConversationConstraints(TestCase):
    def test_one_active_conversation_per_screen(self):
        """The per-screen idempotency ai-service's API documents, enforced in the DB.

        `POST /v1/conversations` is "find the active conversation for this screen, else
        create one" — a read-then-write race that two tabs or a retry can lose.
        """
        screen_uuid = uuid.uuid4()
        make_conversation(screen_uuid=screen_uuid)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_conversation(screen_uuid=screen_uuid)

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

    def test_deleting_a_conversation_removes_its_messages(self):
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
