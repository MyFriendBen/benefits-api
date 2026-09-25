"""
Tests for the language the save-results message is composed in.

The subject and body are built server-side by MessageUser from white-label
config labels, so the language is chosen here rather than by the caller's copy.
"""

import json
from unittest.mock import patch

from django.test import TestCase

from screener.models import Screen, WhiteLabel
from screener.views import MessageViewSet


class FakeRequest:
    """Minimal stand-in: MessageViewSet.create reads request.body directly."""

    def __init__(self, payload: dict):
        self.body = json.dumps(payload).encode()


class TestMessageLanguage(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=True,
            request_language_code="es",
        )

    def resolve(self, payload: dict) -> str:
        return MessageViewSet._message_language(payload, self.screen)

    def test_uses_the_requested_language(self):
        self.assertEqual(self.resolve({"language": "vi"}), "vi")

    def test_falls_back_to_the_screener_language_when_absent(self):
        self.assertEqual(self.resolve({}), "es")

    def test_falls_back_rather_than_erroring_on_an_unsupported_language(self):
        # Sending the results in the screener's language beats refusing to send.
        self.assertEqual(self.resolve({"language": "kl"}), "es")

    def test_falls_back_on_an_empty_language(self):
        self.assertEqual(self.resolve({"language": ""}), "es")
        self.assertEqual(self.resolve({"language": None}), "es")

    def test_accepts_a_language_the_screener_was_not_taken_in(self):
        self.assertEqual(self.resolve({"language": "en-us"}), "en-us")

    def test_normalizes_case(self):
        # The frontend sends config codes like `zh-hans`; be forgiving of casing
        # rather than silently dropping to the screener's language.
        self.assertEqual(self.resolve({"language": "ZH-Hans"}), "zh-hans")

    def test_screener_language_is_used_when_the_screen_has_none(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=True
        )
        self.assertEqual(MessageViewSet._message_language({}, screen), "en-us")


class TestMessageViewThreadsLanguage(TestCase):
    """The resolved language has to actually reach MessageUser."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=True,
            request_language_code="en-us",
        )

    @patch("screener.views.MessageUser")
    def test_email_is_composed_in_the_requested_language(self, mock_message_user):
        request = FakeRequest({"screen": str(self.screen.uuid), "email": "a@example.com", "language": "es"})

        MessageViewSet().create(request)

        mock_message_user.assert_called_once_with(self.screen, "es")
        mock_message_user.return_value.email.assert_called_once_with("a@example.com", send_tests=True)

    @patch("screener.views.MessageUser")
    def test_text_is_composed_in_the_requested_language(self, mock_message_user):
        request = FakeRequest({"screen": str(self.screen.uuid), "phone": "+13035551234", "language": "vi"})

        MessageViewSet().create(request)

        mock_message_user.assert_called_once_with(self.screen, "vi")
        mock_message_user.return_value.text.assert_called_once_with("+13035551234", send_tests=True)

    @patch("screener.views.MessageUser")
    def test_omitted_language_keeps_the_previous_behavior(self, mock_message_user):
        request = FakeRequest({"screen": str(self.screen.uuid), "email": "a@example.com"})

        MessageViewSet().create(request)

        mock_message_user.assert_called_once_with(self.screen, "en-us")
