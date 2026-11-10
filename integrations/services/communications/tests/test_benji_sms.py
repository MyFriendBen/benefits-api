"""Dark-launch guards for Benji SMS (MFB-2433).

The point of these tests: no Benji text reaches Twilio unless the kill switch is on,
the white label's flag is on (for screen sends), DEBUG is off and Twilio is configured.
"""

from contextlib import contextmanager
from typing import Iterator, Optional
from unittest.mock import MagicMock, patch

import requests
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from twilio.base.exceptions import TwilioRestException

from integrations.services.communications import benji_sms
from screener.feature_flags import WHITELABEL_FEATURE_FLAGS
from screener.models import WhiteLabel

_MISSING = object()
PHONE = "+15555550100"
TWILIO = {"TWILIO_SID": "AC" + "0" * 32, "TWILIO_TOKEN": "token", "TWILIO_PHONE_NUMBER": "+15555550199"}


@contextmanager
def switch(value: object = _MISSING) -> Iterator[None]:
    """Set the BENJI_SMS_OUTBOUND_ENABLED setting; _MISSING removes it entirely."""
    with override_settings():
        if value is _MISSING:
            del settings.BENJI_SMS_OUTBOUND_ENABLED
        else:
            setattr(settings, benji_sms.SWITCH, value)
        yield


def make_white_label(flag: Optional[bool]) -> WhiteLabel:
    flags = {} if flag is None else {benji_sms.FLAG: flag}
    return WhiteLabel.objects.create(name="Test", code="test_sms", state_code="TS", feature_flags=flags)


class FlagRegistrationTest(TestCase):
    def test_registered_for_both_sides_and_off_by_default(self) -> None:
        flag = WHITELABEL_FEATURE_FLAGS[benji_sms.FLAG]
        self.assertEqual(flag.scope, "both")
        self.assertFalse(flag.default)

    def test_white_label_without_the_key_reads_off(self) -> None:
        self.assertFalse(make_white_label(flag=None).has_feature(benji_sms.FLAG))

    def test_sync_adds_it_off(self) -> None:
        wl = make_white_label(flag=None)
        call_command("sync_feature_flags", stdout=MagicMock())
        wl.refresh_from_db()
        self.assertIs(wl.feature_flags[benji_sms.FLAG], False)


class OutboundSwitchTest(TestCase):
    def test_missing_is_off(self) -> None:
        with switch():
            self.assertFalse(benji_sms.outbound_enabled())

    def test_off_values(self) -> None:
        for value in ["", "false", "False", "0", "no", "off", "enabled", "ture", " "]:
            with self.subTest(value=value), switch(value):
                self.assertFalse(benji_sms.outbound_enabled())

    def test_on_values(self) -> None:
        for value in ["true", "True", "TRUE", "1", "yes", "on", " true "]:
            with self.subTest(value=value), switch(value):
                self.assertTrue(benji_sms.outbound_enabled())


@override_settings(DEBUG=False, **TWILIO)
class SendTest(TestCase):
    def setUp(self) -> None:
        client_patch = patch.object(benji_sms, "twilio_client")
        self.twilio = client_patch.start()
        self.addCleanup(client_patch.stop)
        self.create = self.twilio.return_value.messages.create
        self.create.return_value.sid = "SM123"

    def screen_send(self, white_label: Optional[WhiteLabel]) -> Optional[str]:
        return benji_sms.send_screen_sms(PHONE, "hello", white_label=white_label)  # type: ignore[arg-type]

    def fixed_reply(self) -> Optional[str]:
        return benji_sms.send_fixed_reply(PHONE, "hello")

    def assert_not_sent(self, result: Optional[str]) -> None:
        self.assertIsNone(result)
        self.create.assert_not_called()

    # Any gate closed: nothing reaches Twilio.

    def test_switch_missing_flag_on(self) -> None:
        with switch():
            self.assert_not_sent(self.screen_send(make_white_label(flag=True)))

    def test_switch_off_flag_on(self) -> None:
        with switch("false"):
            self.assert_not_sent(self.screen_send(make_white_label(flag=True)))

    def test_switch_on_flag_off(self) -> None:
        with switch("true"):
            self.assert_not_sent(self.screen_send(make_white_label(flag=False)))

    def test_switch_on_flag_unset(self) -> None:
        with switch("true"):
            self.assert_not_sent(self.screen_send(make_white_label(flag=None)))

    def test_both_off(self) -> None:
        with switch("false"):
            self.assert_not_sent(self.screen_send(make_white_label(flag=False)))

    def test_screen_send_without_white_label_refuses(self) -> None:
        # A nullable FK passed through must not skip the flag.
        with switch("true"):
            self.assert_not_sent(self.screen_send(None))

    def test_fixed_reply_needs_the_switch(self) -> None:
        with switch():
            self.assert_not_sent(self.fixed_reply())
        with switch("false"):
            self.assert_not_sent(self.fixed_reply())

    @override_settings(DEBUG=True)
    def test_debug_never_sends(self) -> None:
        with switch("true"):
            self.assert_not_sent(self.screen_send(make_white_label(flag=True)))
            self.assert_not_sent(self.fixed_reply())

    def test_missing_twilio_config_never_sends(self) -> None:
        wl = make_white_label(flag=True)
        for key in TWILIO:
            with self.subTest(key=key), switch("true"), override_settings(**{key: ""}):
                self.assert_not_sent(self.screen_send(wl))
                self.assert_not_sent(self.fixed_reply())

    # Every gate open: exactly one send.

    def test_screen_send_when_switch_and_flag_on(self) -> None:
        with switch("true"):
            sid = self.screen_send(make_white_label(flag=True))
        self.assertEqual(sid, "SM123")
        self.create.assert_called_once_with(from_=TWILIO["TWILIO_PHONE_NUMBER"], to=PHONE, body="hello")

    def test_fixed_reply_sends_on_switch_alone(self) -> None:
        with switch("true"):
            self.assertEqual(self.fixed_reply(), "SM123")
        self.create.assert_called_once()

    def test_passes_status_callback(self) -> None:
        with switch("true"):
            benji_sms.send_fixed_reply(PHONE, "hello", status_callback="https://example.test/status")
        self.assertEqual(self.create.call_args.kwargs["status_callback"], "https://example.test/status")

    def test_white_label_is_required_for_screen_sends(self) -> None:
        with switch("true"), self.assertRaises(TypeError):
            benji_sms.send_screen_sms(PHONE, "hello")  # type: ignore[call-arg]
        self.create.assert_not_called()

    # The pre-checks agree with the sends.

    def test_can_send_for_screen(self) -> None:
        on, off = make_white_label(flag=True), WhiteLabel.objects.create(
            name="Off", code="off_sms", feature_flags={benji_sms.FLAG: False}
        )
        with switch("true"):
            self.assertTrue(benji_sms.can_send_for_screen(on))
            self.assertFalse(benji_sms.can_send_for_screen(off))
            self.assertFalse(benji_sms.can_send_for_screen(None))
        with switch("false"):
            self.assertFalse(benji_sms.can_send_for_screen(on))

    def test_can_send_fixed_reply(self) -> None:
        with switch("true"):
            self.assertTrue(benji_sms.can_send_fixed_reply())
        with switch():
            self.assertFalse(benji_sms.can_send_fixed_reply())
        with switch("true"), override_settings(DEBUG=True):
            self.assertFalse(benji_sms.can_send_fixed_reply())

    # Nothing personal leaves in logs or errors.

    def test_refusal_is_logged_with_its_reason_and_no_phone_or_body(self) -> None:
        with switch("true"), self.assertLogs(benji_sms.logger, level="WARNING") as logs:
            self.screen_send(make_white_label(flag=False))
        self.assertEqual(len(logs.output), 1)
        self.assertIn("reason=flag_off", logs.output[0])
        self.assertIn("white_label=test_sms", logs.output[0])
        self.assertNotIn("5555550100", logs.output[0])
        self.assertNotIn("hello", logs.output[0])

    def test_twilio_error_is_reraised_without_the_number(self) -> None:
        self.create.side_effect = TwilioRestException(
            400, "/Messages.json", msg=f"The 'To' number {PHONE} is not a valid phone number.", code=21211
        )
        with switch("true"), self.assertRaises(benji_sms.BenjiSmsSendError) as ctx:
            self.fixed_reply()
        err = ctx.exception
        self.assertEqual((err.status, err.code), (400, 21211))
        self.assertNotIn("5555550100", str(err))
        # Chain suppressed, so error reporters don't pick up Twilio's message.
        self.assertIsNone(err.__cause__)
        self.assertTrue(err.__suppress_context__)

    def test_connect_timeout_is_not_sent(self) -> None:
        self.create.side_effect = requests.ConnectTimeout("api.twilio.com")
        with switch("true"), self.assertRaises(benji_sms.BenjiSmsSendError) as ctx:
            self.fixed_reply()
        self.assertTrue(ctx.exception.__suppress_context__)

    def test_read_timeout_and_dropped_connection_are_delivery_unknown(self) -> None:
        for exc in [requests.ReadTimeout("slow"), requests.ConnectionError("reset")]:
            with self.subTest(exc=type(exc).__name__), switch("true"):
                self.create.side_effect = exc
                with self.assertRaises(benji_sms.BenjiSmsDeliveryUnknown) as ctx:
                    self.screen_send(make_white_label(flag=True))
                err = ctx.exception
                self.assertEqual(err.cause, type(exc).__name__)
                self.assertTrue(err.__suppress_context__)
                # Not a BenjiSmsSendError, so `except BenjiSmsSendError: retry` can't resend it.
                self.assertNotIsInstance(err, benji_sms.BenjiSmsSendError)
                self.assertIsInstance(err, benji_sms.BenjiSmsError)
                WhiteLabel.objects.filter(code="test_sms").delete()
