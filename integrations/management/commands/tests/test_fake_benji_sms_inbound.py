from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from twilio.request_validator import RequestValidator

from integrations.management.commands import fake_benji_sms_inbound as cmd

URL = "http://localhost:8000/api/assistant/sms/inbound/"
TOKEN = "local-test-token"


@override_settings(DEBUG=True, BACKEND_DOMAIN="http://localhost:8000")
class FakeBenjiSmsInboundTest(SimpleTestCase):
    def setUp(self):
        post = patch.object(cmd.requests, "post")
        self.post = post.start()
        self.post.return_value = MagicMock(status_code=200, text="<Response/>")
        self.addCleanup(post.stop)

    def run_cmd(self, *args: str) -> str:
        out = StringIO()
        call_command("fake_benji_sms_inbound", *args, "--token", TOKEN, stdout=out)
        return out.getvalue()

    def posted(self) -> tuple[str, dict[str, str], str]:
        call = self.post.call_args
        return call.args[0], call.kwargs["data"], call.kwargs["headers"]["X-Twilio-Signature"]

    def test_signature_validates_as_twilio_would(self):
        self.run_cmd("what is snap")
        url, data, signature = self.posted()
        self.assertEqual(url, URL)
        self.assertTrue(RequestValidator(TOKEN).validate(url, data, signature))
        self.assertFalse(RequestValidator("another-token").validate(url, data, signature))

    def test_fields_look_like_an_inbound_message(self):
        self.run_cmd("STOP", "--from", "+15555550123", "--to", "+15555550199")
        _, data, _ = self.posted()
        self.assertEqual(data["Body"], "STOP")
        self.assertEqual(data["From"], "+15555550123")
        self.assertEqual(data["To"], "+15555550199")
        self.assertEqual(data["NumMedia"], "0")
        self.assertTrue(data["MessageSid"].startswith("SM"))
        self.assertEqual(data["MessageSid"], data["SmsSid"])

    def test_reused_sid_for_replays(self):
        sid = "SM" + "a" * 32
        self.run_cmd("hi", "--sid", sid)
        self.assertEqual(self.posted()[1]["MessageSid"], sid)

    def test_media(self):
        self.run_cmd("", "--media", "2")
        _, data, _ = self.posted()
        self.assertEqual(data["NumMedia"], "2")
        self.assertIn("MediaUrl1", data)
        self.assertNotIn("MediaUrl2", data)

    def test_prints_status(self):
        self.assertIn("200", self.run_cmd("hi"))

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaisesMessage(CommandError, "DEBUG"):
            self.run_cmd("hi")
        self.post.assert_not_called()

    def test_refuses_remote_urls(self):
        for url in ["https://benefits-api.example.org/api/assistant/sms/inbound/", "http://10.0.0.5/x"]:
            with self.subTest(url=url), self.assertRaisesMessage(CommandError, "only local"):
                self.run_cmd("hi", "--url", url)
        self.post.assert_not_called()

    def test_needs_a_token(self):
        with patch.object(cmd, "config", return_value=""), self.assertRaisesMessage(CommandError, "token"):
            call_command("fake_benji_sms_inbound", "hi", stdout=StringIO())
        self.post.assert_not_called()

    def test_server_not_running(self):
        self.post.side_effect = requests.ConnectionError()
        with self.assertRaisesMessage(CommandError, "dev server"):
            self.run_cmd("hi")
