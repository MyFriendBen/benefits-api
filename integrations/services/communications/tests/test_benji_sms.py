"""Dark-launch guards for Benji SMS (MFB-2433).

The point of these tests: no Benji text reaches Twilio unless the kill switch is on,
the white label's flag is on (for per-screen sends), and DEBUG is off.
"""

from contextlib import contextmanager
from typing import Iterator, Optional
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from integrations.services.communications import benji_sms
from screener.feature_flags import WHITELABEL_FEATURE_FLAGS
from screener.models import WhiteLabel

_MISSING = object()


@contextmanager
def switch(value: object = _MISSING) -> Iterator[None]:
    """Set BENJI_SMS_OUTBOUND_ENABLED as decouple would see it; _MISSING means unset.

    Patches the module's config lookup rather than os.environ, so a developer's .env
    can never leak a value into these tests.
    """

    def fake_config(key: str, default: object = "", **kwargs: object) -> object:
        if key == benji_sms.SWITCH:
            return default if value is _MISSING else value
        return default

    with patch.object(benji_sms, "config", side_effect=fake_config):
        yield


def make_white_label(flag: Optional[bool]) -> WhiteLabel:
    flags = {} if flag is None else {benji_sms.FLAG: flag}
    return WhiteLabel.objects.create(name="Test", code="test_sms", state_code="TS", feature_flags=flags)


class FlagRegistrationTest(TestCase):
    def test_registered_for_both_sides_and_off_by_default(self):
        flag = WHITELABEL_FEATURE_FLAGS[benji_sms.FLAG]
        self.assertEqual(flag.scope, "both")
        self.assertFalse(flag.default)

    def test_white_label_without_the_key_reads_off(self):
        self.assertFalse(make_white_label(flag=None).has_feature(benji_sms.FLAG))

    def test_sync_adds_it_off(self):
        wl = make_white_label(flag=None)
        call_command("sync_feature_flags", stdout=MagicMock())
        wl.refresh_from_db()
        self.assertIs(wl.feature_flags[benji_sms.FLAG], False)


class OutboundSwitchTest(TestCase):
    def test_missing_is_off(self):
        with switch():
            self.assertFalse(benji_sms.outbound_enabled())

    def test_off_values(self):
        for value in ["", "false", "False", "0", "no", "off", "enabled", "ture", " "]:
            with self.subTest(value=value), switch(value):
                self.assertFalse(benji_sms.outbound_enabled())

    def test_on_values(self):
        for value in ["true", "True", "TRUE", "1", "yes", "on", " true "]:
            with self.subTest(value=value), switch(value):
                self.assertTrue(benji_sms.outbound_enabled())


@override_settings(DEBUG=False)
class SendBenjiSmsTest(TestCase):
    def setUp(self):
        self.client_patch = patch.object(benji_sms, "_client")
        self.twilio = self.client_patch.start()
        self.twilio.return_value.messages.create.return_value.sid = "SM123"
        self.addCleanup(self.client_patch.stop)

    def send(self, white_label: Optional[WhiteLabel]) -> Optional[str]:
        return benji_sms.send_benji_sms("+15555550100", "hello", white_label=white_label)

    def assert_not_sent(self, result: Optional[str]) -> None:
        self.assertIsNone(result)
        self.twilio.assert_not_called()

    # Either gate off: nothing reaches Twilio.

    def test_switch_missing_flag_on(self):
        with switch():
            self.assert_not_sent(self.send(make_white_label(flag=True)))

    def test_switch_off_flag_on(self):
        with switch("false"):
            self.assert_not_sent(self.send(make_white_label(flag=True)))

    def test_switch_on_flag_off(self):
        with switch("true"):
            self.assert_not_sent(self.send(make_white_label(flag=False)))

    def test_switch_on_flag_unset(self):
        with switch("true"):
            self.assert_not_sent(self.send(make_white_label(flag=None)))

    def test_both_off(self):
        with switch("false"):
            self.assert_not_sent(self.send(make_white_label(flag=False)))

    def test_fixed_reply_without_white_label_needs_the_switch(self):
        with switch():
            self.assert_not_sent(self.send(None))
        with switch("false"):
            self.assert_not_sent(self.send(None))

    @override_settings(DEBUG=True)
    def test_debug_never_sends(self):
        with switch("true"):
            self.assert_not_sent(self.send(make_white_label(flag=True)))
            self.assert_not_sent(self.send(None))

    # Every gate open: exactly one send.

    def test_sends_when_switch_and_flag_on(self):
        with switch("true"):
            sid = self.send(make_white_label(flag=True))
        self.assertEqual(sid, "SM123")
        self.twilio.return_value.messages.create.assert_called_once()
        kwargs = self.twilio.return_value.messages.create.call_args.kwargs
        self.assertEqual(kwargs["to"], "+15555550100")
        self.assertEqual(kwargs["body"], "hello")
        self.assertNotIn("status_callback", kwargs)

    def test_fixed_reply_without_white_label_sends_on_switch_alone(self):
        with switch("true"):
            self.assertEqual(self.send(None), "SM123")
        self.twilio.return_value.messages.create.assert_called_once()

    def test_passes_status_callback(self):
        with switch("true"):
            benji_sms.send_benji_sms(
                "+15555550100", "hello", white_label=None, status_callback="https://example.test/status"
            )
        kwargs = self.twilio.return_value.messages.create.call_args.kwargs
        self.assertEqual(kwargs["status_callback"], "https://example.test/status")

    def test_white_label_is_required(self):
        with switch("true"), self.assertRaises(TypeError):
            benji_sms.send_benji_sms("+15555550100", "hello")  # type: ignore[call-arg]
        self.twilio.assert_not_called()

    def test_refusal_log_has_no_phone_or_body(self):
        with switch("false"), self.assertLogs(benji_sms.logger, level="INFO") as logs:
            self.send(make_white_label(flag=True))
        record = logs.records[0]
        self.assertEqual(record.reason, "switch_off")
        self.assertEqual(record.white_label, "test_sms")
        rendered = " ".join(logs.output) + repr(record.__dict__)
        self.assertNotIn("5555550100", rendered)
        self.assertNotIn("hello", rendered)
