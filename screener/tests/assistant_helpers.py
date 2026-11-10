"""Shared factories for tests of the Benji tables (conversations, messages, SMS).

Kept out of the test modules so one test file never imports another.
"""

import uuid
from typing import Any

from screener.models import AssistantConversation, AssistantMessage


def make_conversation(**overrides: Any) -> AssistantConversation:
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


def make_message(conversation: AssistantConversation, seq: int, **overrides: Any) -> AssistantMessage:
    defaults = {
        "message_id": uuid.uuid4(),
        "conversation": conversation,
        "seq": seq,
        "role": "user",
        "text": "hello",
    }
    return AssistantMessage.objects.create(**{**defaults, **overrides})
