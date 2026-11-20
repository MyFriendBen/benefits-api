"""The Benji SMS inbound webhook (MFB-2439).

What these pin: a request Twilio did not sign is refused before anything is read from
the database; every row of the decision table in
integrations/services/communications/benji_sms_inbound.py does what it says; a replayed
webhook changes nothing new, consent included; a text that cannot be queued gets a 503
so Twilio posts it again, after any STOP in it has been applied; and nothing logged
carries the number, its hash or the message.

Requests are built and signed by the fake-inbound command's own helpers, so the command
and the view cannot drift apart.
"""

import threading
from datetime import timedelta
from typing import Any, Optional
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import requests
from twilio.base.exceptions import TwilioRestException
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import path
from django.utils import timezone

from integrations.management.commands.fake_benji_sms_inbound import build_params, sign
from benefits.urls import urlpatterns as project_urlpatterns
from integrations.services.communications import benji_sms
from integrations.services.communications import benji_sms_inbound as inbound_service
from integrations.services.communications import benji_sms_replies as replies
from integrations.services.communications.benji_sms_hash import phone_hash
from screener import benji_sms_inbound
from screener.models import (
    BENJI_SMS_QUIET_INTERVAL,
    AssistantChannel,
    AssistantConversationStatus,
    BenjiSmsBinding,
    BenjiSmsDelivery,
    BenjiSmsDeliveryKind,
    BenjiSmsPhone,
    BenjiSmsStrangerReply,
    WhiteLabel,
)
from screener.tasks import BrokerNotConfigured
from screener.tests.assistant_helpers import make_conversation

TOKEN = "test-twilio-token"
ORIGIN = "https://api.example.test"
FRONTEND = "https://screener.example.test"
INBOUND_PATH = "/api/assistant/sms/inbound/"
FALLBACK_PATH = "/api/assistant/sms/inbound/fallback/"
PHONE = "+13035550100"
OTHER_PHONE = "+13035550101"
OUR_NUMBER = "+15555550199"
SID = "SM" + "a1" * 16
OTHER_SID = "SM" + "b2" * 16
LOGGER = "screener.benji_sms_inbound"
SERVICE_LOGGER = "integrations.services.communications.benji_sms_inbound"
STATUS_PATH = "/api/assistant/sms/status/"


def _status_callback_stub(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


# The project's routes plus a stand-in for the status callback route (MFB-2441), for
# the test that shows sends ask for delivery status once that route exists.
urlpatterns = [*project_urlpatterns, path(STATUS_PATH.lstrip("/"), _status_callback_stub, name="benji-sms-status")]

SETTINGS: dict[str, Any] = {
    "DEBUG": False,
    "TWILIO_SID": "AC" + "0" * 32,
    "TWILIO_TOKEN": TOKEN,
    "TWILIO_PHONE_NUMBER": OUR_NUMBER,
    "BACKEND_DOMAIN": ORIGIN,
    "FRONTEND_DOMAIN": FRONTEND,
    "BENJI_SMS_HASH_KEY": "k" * 64,
    "BENJI_SMS_OUTBOUND_ENABLED": "true",
}


class InboundMixin:
    """Signed posts, a mocked Twilio and a mocked queue."""

    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        client_patch = patch.object(benji_sms, "twilio_client")
        self.create = client_patch.start().return_value.messages.create
        self.addCleanup(client_patch.stop)  # type: ignore[attr-defined]
        self._outbound = 0
        self.create.side_effect = self._accept

        for name in ("enqueue_turn", "enqueue_media_deletion"):
            queue_patch = patch.object(inbound_service, name)
            setattr(self, name, queue_patch.start())
            self.addCleanup(queue_patch.stop)  # type: ignore[attr-defined]

        self.white_label = WhiteLabel.objects.create(
            name="Test", code="test_sms", state_code="TS", feature_flags={benji_sms.FLAG: True}
        )

    def _accept(self, **_kwargs: Any) -> MagicMock:
        self._outbound += 1
        return MagicMock(sid=f"SM{self._outbound:032x}")

    def post(
        self,
        body: str = "what is snap",
        *,
        sender: str = PHONE,
        sid: str = SID,
        media: int = 0,
        path: str = INBOUND_PATH,
        token: str = TOKEN,
        signed_url: Optional[str] = None,
        extra: Optional[dict[str, str]] = None,
    ) -> HttpResponse:
        params = {**build_params(body, sender, OUR_NUMBER, sid, media), **(extra or {})}
        signature = sign(token, signed_url or ORIGIN + path, params)
        return self.client.post(  # type: ignore[attr-defined]
            path,
            data=urlencode(params),
            content_type="application/x-www-form-urlencoded",
            HTTP_X_TWILIO_SIGNATURE=signature,
        )

    def bind(self, number: str = PHONE, **overrides: Any) -> BenjiSmsBinding:
        """An on-ramped number: a phone row with an active binding and SMS conversation."""
        phone, _ = BenjiSmsPhone.objects.get_or_create(phone_hash=phone_hash(number))
        if "conversation" not in overrides:
            overrides["conversation"] = make_conversation(
                white_label=self.white_label.code, channel=AssistantChannel.SMS, locale="en-us"
            )
        defaults = {
            "phone": phone,
            "white_label": self.white_label,
            "consented_at": timezone.now(),
            "consent_version": "benji.sms.consent-v1",
        }
        return BenjiSmsBinding.objects.create(**{**defaults, **overrides})

    def sent_bodies(self) -> list[str]:
        return [call.kwargs["body"] for call in self.create.call_args_list]

    def assert_acknowledged(self, response: HttpResponse) -> None:
        self.assertEqual(response.status_code, 200)  # type: ignore[attr-defined]
        self.assertEqual(response["Content-Type"], "text/xml")  # type: ignore[attr-defined]
        self.assertEqual(response.content.decode(), benji_sms_inbound.EMPTY_TWIML)  # type: ignore[attr-defined]

    def assert_nothing_sent_or_queued(self) -> None:
        self.create.assert_not_called()
        self.enqueue_turn.assert_not_called()  # type: ignore[attr-defined]


@override_settings(**SETTINGS)
class SignatureTest(InboundMixin, TestCase):
    def assert_rejected(self, response: HttpResponse) -> None:
        self.assertEqual(response.status_code, 403)
        self.assert_nothing_sent_or_queued()
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())

    def test_an_unsigned_request_is_rejected_before_any_lookup(self) -> None:
        params = build_params("hi", PHONE, OUR_NUMBER, SID, 0)
        with self.assertNumQueries(0):
            response = self.client.post(
                INBOUND_PATH, data=urlencode(params), content_type="application/x-www-form-urlencoded"
            )
        self.assert_rejected(response)

    def test_a_rejected_picture_queues_no_media_deletion(self) -> None:
        params = build_params("", PHONE, OUR_NUMBER, SID, 1)
        with self.assertNumQueries(0):
            response = self.client.post(
                INBOUND_PATH, data=urlencode(params), content_type="application/x-www-form-urlencoded"
            )
        self.assert_rejected(response)
        self.enqueue_media_deletion.assert_not_called()

    def test_a_wrong_signature_is_rejected_before_any_lookup(self) -> None:
        with self.assertNumQueries(0):
            response = self.post(token="someone-elses-token")
        self.assert_rejected(response)

    def test_without_a_token_nothing_validates(self) -> None:
        """An empty key would let anyone compute the signature."""
        with override_settings(TWILIO_TOKEN=""):
            self.assert_rejected(self.post(token=""))

    def test_the_signed_url_is_the_public_one_not_the_host_header(self) -> None:
        self.assert_rejected(self.post(signed_url="http://testserver" + INBOUND_PATH))

    def test_a_signature_for_one_url_does_not_open_another(self) -> None:
        self.assert_rejected(self.post(path=FALLBACK_PATH, signed_url=ORIGIN + INBOUND_PATH))

    def test_a_tampered_field_is_rejected(self) -> None:
        params = build_params("hi", PHONE, OUR_NUMBER, SID, 0)
        signature = sign(TOKEN, ORIGIN + INBOUND_PATH, params)
        params["From"] = OTHER_PHONE
        response = self.client.post(
            INBOUND_PATH,
            data=urlencode(params),
            content_type="application/x-www-form-urlencoded",
            HTTP_X_TWILIO_SIGNATURE=signature,
        )
        self.assert_rejected(response)

    def test_a_json_body_is_not_twilio(self) -> None:
        response = self.client.post(
            INBOUND_PATH, data={"From": PHONE}, content_type="application/json", HTTP_X_TWILIO_SIGNATURE="x"
        )
        self.assertIn(response.status_code, (403, 415))
        self.assert_nothing_sent_or_queued()

    def test_a_signed_request_without_a_message_sid_is_a_400(self) -> None:
        with self.assertLogs(LOGGER, level="WARNING"):
            response = self.post(sid="not-a-sid")
        self.assertEqual(response.status_code, 400)
        self.assert_nothing_sent_or_queued()

    def test_a_trailing_slash_on_backend_domain_does_not_break_validation(self) -> None:
        with override_settings(BACKEND_DOMAIN=ORIGIN + "/"):
            self.assert_acknowledged(self.post())


@override_settings(**SETTINGS)
class StrangerTest(InboundMixin, TestCase):
    def test_a_stranger_gets_the_bilingual_reply_once(self) -> None:
        self.assert_acknowledged(self.post())

        self.create.assert_called_once()
        sent = self.create.call_args.kwargs
        self.assertEqual(sent["to"], PHONE)
        self.assertEqual(sent["from_"], OUR_NUMBER)
        self.assertIn("MyFriendBen", sent["body"])
        self.assertIn("Responda STOP", sent["body"])
        self.assertIn(FRONTEND, sent["body"])
        self.assertNotIn("{link}", sent["body"])
        self.enqueue_turn.assert_not_called()

    def test_it_leaves_a_stranger_row_and_a_delivery_row_but_no_phone_row(self) -> None:
        self.post()

        self.assertEqual(BenjiSmsStrangerReply.objects.get().phone_hash, phone_hash(PHONE))
        delivery = BenjiSmsDelivery.objects.get()
        self.assertEqual(delivery.kind, BenjiSmsDeliveryKind.FIXED)
        self.assertIsNone(delivery.binding)
        self.assertEqual(delivery.inbound_sid, SID)
        self.assertEqual(delivery.outbound_sid, f"SM{1:032x}")
        self.assertIsNotNone(delivery.sent_at)
        self.assertFalse(BenjiSmsPhone.objects.exists())

    def test_a_second_text_that_day_gets_silence(self) -> None:
        self.post()
        self.assert_acknowledged(self.post("hello??", sid=OTHER_SID))

        self.create.assert_called_once()
        self.assertEqual(BenjiSmsDelivery.objects.count(), 1)

    def test_a_text_a_day_later_gets_the_reply_again(self) -> None:
        self.post()
        BenjiSmsStrangerReply.objects.update(replied_at=timezone.now() - timedelta(hours=25))

        self.post(sid=OTHER_SID)

        self.assertEqual(self.create.call_count, 2)

    def test_two_strangers_each_get_a_reply(self) -> None:
        self.post()
        self.post(sender=OTHER_PHONE, sid=OTHER_SID)

        self.assertEqual([call.kwargs["to"] for call in self.create.call_args_list], [PHONE, OTHER_PHONE])

    def test_a_replay_sends_nothing_new(self) -> None:
        self.post()
        self.assert_acknowledged(self.post())

        self.create.assert_called_once()
        self.assertEqual(BenjiSmsDelivery.objects.count(), 1)
        self.assertEqual(BenjiSmsStrangerReply.objects.count(), 1)

    def test_a_keyword_from_a_stranger_gets_nothing(self) -> None:
        """Twilio answered its own keywords, and our STOP and START words have no row to change."""
        for index, body in enumerate(["STOP", "help", "START", "alto", "iniciar", "yes"]):
            with self.subTest(body=body):
                self.assert_acknowledged(self.post(body, sid=f"SM{index:032x}"))
        self.assert_nothing_sent_or_queued()
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())
        self.assertFalse(BenjiSmsPhone.objects.exists())

    def test_our_help_word_from_a_stranger_gets_the_stranger_reply(self) -> None:
        """Twilio does not answer "ayuda", and the stranger reply is the help we have."""
        self.assert_acknowledged(self.post("¡Ayuda!"))
        self.assert_acknowledged(self.post("ayuda", sid=OTHER_SID))

        self.assertEqual(self.create.call_count, 1)
        self.assertIn("Responda STOP", self.sent_bodies()[0])
        self.assertFalse(BenjiSmsPhone.objects.exists())

    def test_a_replay_a_day_later_does_not_spend_the_new_days_reply(self) -> None:
        """The inbound's fixed reply is claimed before the day's."""
        self.post()
        BenjiSmsStrangerReply.objects.update(replied_at=timezone.now() - timedelta(hours=25))

        self.post()
        self.assertEqual(self.create.call_count, 1)

        self.post("hello again", sid=OTHER_SID)
        self.assertEqual(self.create.call_count, 2)

    def test_a_failed_text_lookup_leaves_no_claim_so_the_replay_replies(self) -> None:
        with patch.object(inbound_service.replies, "reply_text", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(BenjiSmsDelivery.objects.exists())
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())

        self.assert_acknowledged(self.post())
        self.create.assert_called_once()

    def test_with_the_kill_switch_off_nothing_is_sent_and_the_day_is_not_spent(self) -> None:
        with override_settings(BENJI_SMS_OUTBOUND_ENABLED=""):
            self.assert_acknowledged(self.post())

        self.create.assert_not_called()
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())
        self.assertFalse(BenjiSmsDelivery.objects.exists())

    def test_a_sender_that_is_not_a_phone_number_gets_nothing(self) -> None:
        for index, sender in enumerate(["12345", "MYBANK"]):
            with self.subTest(sender=sender):
                self.assert_acknowledged(self.post(sender=sender, sid=f"SM{index:032x}"))
        self.assert_nothing_sent_or_queued()
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())


@override_settings(**SETTINGS)
class SendFailureTest(InboundMixin, TestCase):
    def test_a_refused_send_is_logged_by_code_and_still_acknowledged(self) -> None:
        self.create.side_effect = TwilioRestException(400, "uri", f"The number {PHONE} is invalid", 21211)

        with self.assertLogs(SERVICE_LOGGER, level="ERROR") as logs:
            self.assert_acknowledged(self.post())

        self.assertIn("code=21211", logs.output[0])
        self.assertNotIn(PHONE, "".join(logs.output))
        self.assertFalse(BenjiSmsDelivery.objects.exists())

    def test_a_send_to_an_opted_out_number_is_a_warning_not_an_alarm(self) -> None:
        self.create.side_effect = TwilioRestException(400, "uri", "unsubscribed", 21610)

        with self.assertLogs(SERVICE_LOGGER, level="WARNING") as logs:
            self.assert_acknowledged(self.post())

        self.assertEqual({record.levelname for record in logs.records}, {"WARNING"})
        self.assertIn("code=21610", logs.output[0])

    def test_a_refusal_that_will_not_pass_keeps_the_days_claim(self) -> None:
        """The same number would be refused again: one attempt a day."""
        self.create.side_effect = TwilioRestException(400, "uri", "invalid", 21211)
        with self.assertLogs(SERVICE_LOGGER, level="ERROR"):
            self.post()

        self.create.side_effect = self._accept
        self.post("hello?", sid=OTHER_SID)

        self.assertEqual(self.create.call_count, 1)
        self.assertEqual(BenjiSmsStrangerReply.objects.count(), 1)

    def test_a_refusal_that_may_pass_gives_the_days_claim_back(self) -> None:
        for index, failure in enumerate(
            [
                TwilioRestException(500, "uri", "internal", 20500),
                TwilioRestException(429, "uri", "too many", 20429),
                requests.ConnectTimeout("twilio"),
            ]
        ):
            with self.subTest(failure=type(failure).__name__):
                self.create.reset_mock()
                self.create.side_effect = failure
                with self.assertLogs(SERVICE_LOGGER, level="ERROR"):
                    self.post(sid=f"SM{index:031x}a")
                self.assertFalse(BenjiSmsStrangerReply.objects.exists())

                self.create.side_effect = self._accept
                self.post("hello?", sid=f"SM{index:031x}b")
                self.assertEqual(self.create.call_count, 2)
                BenjiSmsStrangerReply.objects.all().delete()

    def test_an_unknown_delivery_keeps_its_row_so_a_replay_does_not_resend(self) -> None:
        """A bound number's HELP, so no daily claim stands between the replay and the row."""
        binding = self.bind()
        self.create.side_effect = requests.ReadTimeout("twilio")

        with self.assertLogs(SERVICE_LOGGER, level="ERROR"):
            self.assert_acknowledged(self.post("¡Ayuda!"))
        delivery = BenjiSmsDelivery.objects.get()
        self.assertIsNone(delivery.outbound_sid)
        self.assertEqual(delivery.binding, binding)
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())

        self.create.side_effect = self._accept
        self.post("¡Ayuda!")
        self.assertEqual(self.create.call_count, 1)
        self.assertEqual(BenjiSmsDelivery.objects.count(), 1)

    def test_a_2xx_without_a_sid_counts_as_unknown_not_refused(self) -> None:
        """Twilio may have queued it: keep the claims, send nothing more."""
        self.create.side_effect = lambda **_kwargs: MagicMock(sid=None)
        with self.assertLogs(SERVICE_LOGGER, level="ERROR"):
            self.post()

        self.assertEqual(BenjiSmsDelivery.objects.count(), 1)
        self.assertTrue(BenjiSmsStrangerReply.objects.exists())
        self.post()
        self.assertEqual(self.create.call_count, 1)

    def test_an_unknown_daily_delivery_keeps_the_days_claim(self) -> None:
        self.create.side_effect = requests.ReadTimeout("twilio")
        with self.assertLogs(SERVICE_LOGGER, level="ERROR"):
            self.post()

        self.create.side_effect = self._accept
        self.post("hello?", sid=OTHER_SID)
        self.assertEqual(self.create.call_count, 1)

    def test_no_status_callback_until_its_route_exists(self) -> None:
        self.post()
        self.assertNotIn("status_callback", self.create.call_args.kwargs)

    @override_settings(ROOT_URLCONF=__name__)
    def test_sends_ask_for_delivery_status_once_the_callback_route_exists(self) -> None:
        self.post()
        self.assertEqual(self.create.call_args.kwargs["status_callback"], ORIGIN + STATUS_PATH)


@override_settings(**SETTINGS)
class StopTest(InboundMixin, TestCase):
    def assert_revoked(self, binding: BenjiSmsBinding) -> None:
        binding.refresh_from_db()
        binding.phone.refresh_from_db()
        binding.conversation.refresh_from_db()
        self.assertIsNotNone(binding.phone.revoked_at)
        self.assertEqual(binding.status, AssistantConversationStatus.CLOSED)
        self.assertEqual(binding.conversation.status, AssistantConversationStatus.CLOSED)

    def test_a_carrier_stop_revokes_and_sends_nothing(self) -> None:
        """Twilio already confirmed, and blocks anything we would send."""
        binding = self.bind()

        self.assert_acknowledged(self.post("STOP"))

        self.assert_revoked(binding)
        self.assert_nothing_sent_or_queued()
        self.assertFalse(BenjiSmsDelivery.objects.exists())

    def test_every_carrier_wording_revokes(self) -> None:
        for index, body in enumerate(["stop", " Stop ", "STOPALL", "unsubscribe", "cancel", "end", "quit", "optout"]):
            with self.subTest(body=body):
                binding = self.bind(f"+1303555{index:04d}")
                self.post(body, sender=f"+1303555{index:04d}", sid=f"SM{index:032x}")
                self.assert_revoked(binding)
        self.assert_nothing_sent_or_queued()

    def test_a_wording_twilio_does_not_handle_revokes_and_confirms(self) -> None:
        binding = self.bind()

        self.assert_acknowledged(self.post("Alto"))

        self.assert_revoked(binding)
        self.assertEqual(self.sent_bodies(), [replies.STOP.default])
        delivery = BenjiSmsDelivery.objects.get()
        self.assertEqual(delivery.binding, binding)
        self.assertEqual(delivery.inbound_sid, SID)
        self.enqueue_turn.assert_not_called()

    def test_a_replayed_stop_confirms_once(self) -> None:
        self.bind()
        self.post("no más")
        self.post("no más")

        self.assertEqual(self.create.call_count, 1)
        self.assertEqual(BenjiSmsDelivery.objects.count(), 1)

    def test_a_second_stop_keeps_the_first_revocation_time(self) -> None:
        binding = self.bind()
        self.post("STOP")
        first = BenjiSmsPhone.objects.get().revoked_at

        self.post("alto", sid=OTHER_SID)

        self.assertEqual(BenjiSmsPhone.objects.get().revoked_at, first)
        self.create.assert_not_called()
        self.assert_revoked(binding)

    def test_opt_out_type_from_twilio_settles_it(self) -> None:
        """With Advanced Opt-Out, Twilio handled the message whatever its wording."""
        binding = self.bind()

        self.post("alto", extra={"OptOutType": "STOP"})

        self.assert_revoked(binding)
        self.create.assert_not_called()

    def test_stop_beats_the_shared_mark(self) -> None:
        binding = self.bind()
        BenjiSmsPhone.objects.update(shared_until=timezone.now() + timedelta(days=5))

        self.post("STOP")

        self.assert_revoked(binding)
        self.create.assert_not_called()

    def test_stop_from_an_expired_number_still_revokes(self) -> None:
        binding = self.bind()
        binding.end(AssistantConversationStatus.EXPIRED)

        self.post("STOP")

        binding.phone.refresh_from_db()
        binding.refresh_from_db()
        self.assertIsNotNone(binding.phone.revoked_at)
        self.assertEqual(binding.status, AssistantConversationStatus.EXPIRED)
        self.create.assert_not_called()

    def test_stop_revokes_with_the_kill_switch_and_the_flag_off(self) -> None:
        """The gates stop sends. They never stop a revocation."""
        binding = self.bind()
        self.white_label.feature_flags = {benji_sms.FLAG: False}
        self.white_label.save()

        with override_settings(BENJI_SMS_OUTBOUND_ENABLED=""):
            self.post("alto")

        self.assert_revoked(binding)
        self.create.assert_not_called()
        self.assertFalse(BenjiSmsDelivery.objects.exists())

    def test_a_sentence_containing_stop_is_a_question(self) -> None:
        binding = self.bind()

        for index, body in enumerate(["stop sending me to that website", "stop 我的福利", "Stop отправлять"]):
            with self.subTest(body=body):
                self.post(body, sid=f"SM{index:032x}")

        binding.phone.refresh_from_db()
        self.assertIsNone(binding.phone.revoked_at)
        self.assertEqual(self.enqueue_turn.call_count, 3)

    def test_a_stop_with_a_picture_revokes_even_when_the_deletion_cannot_be_queued(self) -> None:
        """The state change comes first; the 503 still has Twilio post again for the deletion."""
        binding = self.bind()
        self.enqueue_media_deletion.side_effect = BrokerNotConfigured("no broker")

        with self.assertLogs(LOGGER, level="WARNING"):
            response = self.post("alto", media=1)

        self.assertEqual(response.status_code, 503)
        self.assert_revoked(binding)
        self.assertEqual(self.sent_bodies(), [replies.STOP.default])

        self.enqueue_media_deletion.side_effect = None
        self.assert_acknowledged(self.post("alto", media=1))
        self.enqueue_media_deletion.assert_called_with(SID, binding.conversation_id)
        self.assertEqual(self.create.call_count, 1)

    def test_a_replayed_start_that_changed_nothing_does_not_undo_a_stop(self) -> None:
        """iniciar while not revoked (ignored), alto, then the iniciar posted again."""
        binding = self.bind()
        self.post("iniciar", sid=SID)
        self.post("alto", sid=OTHER_SID)

        self.post("iniciar", sid=SID)

        self.assert_revoked(binding)
        self.assertEqual(self.sent_bodies(), [replies.STOP.default])

    def test_a_replayed_yes_from_before_a_stop_is_not_a_turn(self) -> None:
        """A "yes" whose turn could not be queued, an alto, then Twilio posts the yes again."""
        binding = self.bind()
        self.enqueue_turn.side_effect = BrokerNotConfigured("no broker")
        with self.assertLogs(LOGGER, level="WARNING"):
            self.assertEqual(self.post("yes", sid=SID).status_code, 503)
        self.enqueue_turn.side_effect = None
        self.post("alto", sid=OTHER_SID)

        self.assert_acknowledged(self.post("yes", sid=SID))

        self.assert_revoked(binding)
        self.assertEqual(self.enqueue_turn.call_count, 1)

    def test_a_lost_stop_confirmation_is_not_sent_after_a_newer_start(self) -> None:
        binding = self.bind()
        with patch.object(inbound_service.replies, "reply_text", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.post("alto", sid=SID)
        self.post("iniciar", sid=OTHER_SID)

        self.assert_acknowledged(self.post("alto", sid=SID))

        binding.phone.refresh_from_db()
        self.assertIsNone(binding.phone.revoked_at)
        self.assertEqual(self.sent_bodies(), [replies.START_RESUMED.default])

    def test_an_unknown_stop_confirmation_is_not_sent_again_by_the_next_stop(self) -> None:
        """Twilio may have accepted it: unknown counts as sent."""
        self.bind()
        self.create.side_effect = requests.ReadTimeout("twilio")
        with self.assertLogs(SERVICE_LOGGER, level="ERROR"):
            self.post("alto", sid=SID)
        self.create.side_effect = self._accept

        self.post("alto", sid=OTHER_SID)

        self.assertEqual(self.create.call_count, 1)

    def test_a_lost_stop_confirmation_is_not_resent(self) -> None:
        """Best effort: the replay and the next STOP change nothing and send nothing."""
        binding = self.bind()
        with patch.object(inbound_service.replies, "reply_text", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.assertEqual(self.post("alto", sid=SID).status_code, 503)
        self.assert_revoked(binding)

        self.assert_acknowledged(self.post("alto", sid=SID))
        self.create.side_effect = TwilioRestException(503, "uri", "unavailable", 20503)
        self.post("alto", sid=OTHER_SID)

        self.create.assert_not_called()
        self.assert_revoked(binding)

    def test_a_confirmed_stop_is_not_confirmed_again(self) -> None:
        self.bind()
        self.post("alto", sid=SID)
        self.post("alto", sid=OTHER_SID)

        self.assertEqual(self.sent_bodies(), [replies.STOP.default])

    def test_an_overtaken_stop_replayed_later_sends_nothing(self) -> None:
        """alto (confirmation lost), iniciar, alto, then the first alto again."""
        self.bind()
        with patch.object(inbound_service.replies, "reply_text", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.post("alto", sid=SID)
        self.post("iniciar", sid=OTHER_SID)
        self.post("alto", sid="SM" + "e5" * 16)

        self.post("alto", sid=SID)

        self.assertEqual(self.sent_bodies(), [replies.START_RESUMED.default, replies.STOP.default])

    def test_a_replayed_second_stop_does_not_revoke_after_a_start(self) -> None:
        binding = self.bind()
        self.post("alto", sid=SID)
        self.post("alto", sid=OTHER_SID)
        self.post("iniciar", sid="SM" + "e5" * 16)

        self.post("alto", sid=OTHER_SID)

        binding.phone.refresh_from_db()
        binding.refresh_from_db()
        self.assertIsNone(binding.phone.revoked_at)
        self.assertEqual(binding.status, AssistantConversationStatus.ACTIVE)
        self.assertEqual(self.sent_bodies(), [replies.STOP.default, replies.START_RESUMED.default])

    def test_a_replayed_stop_does_not_undo_a_newer_start(self) -> None:
        binding = self.bind()
        stop_sid, start_sid = SID, OTHER_SID
        self.post("STOP", sid=stop_sid)
        self.post("START", sid=start_sid)

        self.post("STOP", sid=stop_sid)

        binding.phone.refresh_from_db()
        binding.refresh_from_db()
        self.assertIsNone(binding.phone.revoked_at)
        self.assertEqual(binding.status, AssistantConversationStatus.ACTIVE)


@override_settings(**SETTINGS)
class RevokedTest(InboundMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.binding = self.bind()
        self.phone = self.binding.phone
        self.phone.revoke()

    def reload(self) -> None:
        self.phone.refresh_from_db()
        self.binding.refresh_from_db()
        self.binding.conversation.refresh_from_db()

    def test_a_revoked_number_gets_silence(self) -> None:
        for index, body in enumerate(["what is snap", "HELP", "ayuda", "hello?"]):
            with self.subTest(body=body):
                self.assert_acknowledged(self.post(body, sid=f"SM{index:032x}"))
        self.assert_nothing_sent_or_queued()
        self.reload()
        self.assertIsNotNone(self.phone.revoked_at)

    def test_a_carrier_start_resumes_and_sends_nothing(self) -> None:
        self.assert_acknowledged(self.post("START"))

        self.reload()
        self.assertIsNone(self.phone.revoked_at)
        self.assertEqual(self.binding.status, AssistantConversationStatus.ACTIVE)
        self.assertEqual(self.binding.conversation.status, AssistantConversationStatus.ACTIVE)
        self.assert_nothing_sent_or_queued()

    def test_after_start_the_next_text_is_a_turn(self) -> None:
        self.post("unstop")
        self.post("what is snap", sid=OTHER_SID)

        self.enqueue_turn.assert_called_once_with(self.binding.conversation_id, OTHER_SID)

    def test_a_start_wording_twilio_does_not_handle_gets_our_reply(self) -> None:
        self.post("Iniciar")

        self.reload()
        self.assertIsNone(self.phone.revoked_at)
        self.assertEqual(self.sent_bodies(), [replies.START_RESUMED.default])

    def test_yes_from_a_revoked_number_is_a_start(self) -> None:
        self.post("yes")

        self.reload()
        self.assertIsNone(self.phone.revoked_at)
        self.assert_nothing_sent_or_queued()

    def test_a_replayed_yes_is_not_then_a_question(self) -> None:
        """Once the yes has cleared the revocation, its replay is not queued as a turn."""
        self.post("yes")
        self.post("yes")

        self.reload()
        self.assertIsNone(self.phone.revoked_at)
        self.assert_nothing_sent_or_queued()

    def test_a_replayed_yes_that_was_an_answer_is_queued_in_its_conversation(self) -> None:
        self.post("START")
        self.post("yes", sid=OTHER_SID)
        self.post("yes", sid=OTHER_SID)

        self.assertEqual(
            [call.args for call in self.enqueue_turn.call_args_list],
            [(self.binding.conversation_id, OTHER_SID)] * 2,
        )

    def test_a_yes_whose_first_post_failed_is_answered_on_the_replay(self) -> None:
        self.post("START")
        with patch.object(inbound_service, "channel_enabled", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.assertEqual(self.post("yes", sid=OTHER_SID).status_code, 503)

        self.assert_acknowledged(self.post("yes", sid=OTHER_SID))

        self.enqueue_turn.assert_called_once_with(self.binding.conversation_id, OTHER_SID)

    def test_an_unfinished_yes_replayed_after_a_stop_is_not_a_turn(self) -> None:
        self.post("START")
        with patch.object(inbound_service, "channel_enabled", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.post("yes", sid=OTHER_SID)
        self.post("alto", sid="SM" + "e5" * 16)

        self.post("yes", sid=OTHER_SID)

        self.enqueue_turn.assert_not_called()
        self.reload()
        self.assertIsNotNone(self.phone.revoked_at)

    def test_a_fresh_yes_after_start_is_an_ordinary_answer(self) -> None:
        self.post("START")
        self.post("yes", sid=OTHER_SID)

        self.enqueue_turn.assert_called_once_with(self.binding.conversation_id, OTHER_SID)

    def test_start_always_clears_but_an_expired_conversation_stays_expired(self) -> None:
        """Left revoked, the number could never on-ramp again."""
        BenjiSmsBinding.objects.update(created_at=timezone.now() - BENJI_SMS_QUIET_INTERVAL - timedelta(days=1))

        self.post("iniciar")

        self.reload()
        self.assertIsNone(self.phone.revoked_at)
        self.assertEqual(self.binding.status, AssistantConversationStatus.CLOSED)
        self.assertEqual(self.sent_bodies(), [replies.START_REENTRY.default])

    def test_start_does_not_resume_into_a_screen_another_phone_now_holds(self) -> None:
        other = make_conversation(
            screen_uuid=self.binding.conversation.screen_uuid,
            white_label=self.white_label.code,
            channel=AssistantChannel.SMS,
        )
        self.bind(OTHER_PHONE, conversation=other)

        self.post("START")

        self.reload()
        self.assertIsNone(self.phone.revoked_at)
        self.assertEqual(self.binding.status, AssistantConversationStatus.CLOSED)
        self.assertEqual(self.binding.conversation.status, AssistantConversationStatus.CLOSED)

    def test_a_replayed_start_changes_nothing_more(self) -> None:
        self.post("iniciar")
        self.post("iniciar")

        self.assertEqual(self.create.call_count, 1)
        self.enqueue_turn.assert_not_called()

    def test_a_replayed_start_does_not_undo_a_newer_stop(self) -> None:
        """iniciar, then alto, then Twilio posts the iniciar again: the alto stands."""
        start_sid, stop_sid = SID, OTHER_SID
        self.post("iniciar", sid=start_sid)
        self.post("alto", sid=stop_sid)

        self.post("iniciar", sid=start_sid)

        self.reload()
        self.assertIsNotNone(self.phone.revoked_at)
        self.assertEqual(self.binding.status, AssistantConversationStatus.CLOSED)
        self.assertEqual(self.sent_bodies(), [replies.START_RESUMED.default, replies.STOP.default])

    def test_a_replay_from_further_back_does_not_undo_the_latest_stop(self) -> None:
        start1, stop2, replayed = SID, OTHER_SID, SID
        self.post("iniciar", sid=start1)
        self.post("alto", sid=stop2)
        self.post("iniciar", sid="SM" + "e5" * 16)
        self.post("alto", sid="SM" + "f6" * 16)

        self.post("iniciar", sid=replayed)

        self.reload()
        self.assertIsNotNone(self.phone.revoked_at)
        self.assertEqual(self.binding.status, AssistantConversationStatus.CLOSED)
        self.assertEqual(self.create.call_count, 4)

    def test_a_lost_start_confirmation_is_not_sent_after_a_newer_stop(self) -> None:
        start, stop = SID, OTHER_SID
        with patch.object(inbound_service.replies, "reply_text", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.post("iniciar", sid=start)
        self.post("alto", sid=stop)

        self.assert_acknowledged(self.post("iniciar", sid=start))

        self.reload()
        self.assertIsNotNone(self.phone.revoked_at)
        self.assertEqual(self.sent_bodies(), [replies.STOP.default])

    def test_a_lost_start_confirmation_is_not_sent_after_a_newer_start(self) -> None:
        start, stop, restart = SID, OTHER_SID, "SM" + "e5" * 16
        with patch.object(inbound_service.replies, "reply_text", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.post("iniciar", sid=start)
        self.post("alto", sid=stop)
        self.post("reanudar", sid=restart)

        self.post("iniciar", sid=start)

        self.assertEqual(self.sent_bodies(), [replies.STOP.default, replies.START_RESUMED.default])

    def test_an_overtaken_yes_replayed_later_is_not_a_question(self) -> None:
        """yes clears, alto, iniciar, then Twilio posts the yes again."""
        self.post("yes", sid=SID)
        self.post("alto", sid=OTHER_SID)
        self.post("iniciar", sid="SM" + "e5" * 16)

        self.assert_acknowledged(self.post("yes", sid=SID))

        self.enqueue_turn.assert_not_called()
        self.reload()
        self.assertIsNone(self.phone.revoked_at)

    def test_a_stop_landing_after_the_start_stops_its_reply(self) -> None:
        original = BenjiSmsPhone.clear_revocation

        def then_stop(self_phone: BenjiSmsPhone, *args: Any, **kwargs: Any) -> Any:
            outcome = original(self_phone, *args, **kwargs)
            BenjiSmsPhone.objects.get(pk=self_phone.pk).revoke()
            return outcome

        with patch.object(BenjiSmsPhone, "clear_revocation", then_stop):
            with self.assertLogs(LOGGER, level="INFO") as logs:
                self.assert_acknowledged(self.post("iniciar"))

        # The START was applied, then the STOP: no "Benji is back" to a revoked number.
        self.assert_nothing_sent_or_queued()
        self.assertIn("replied=False", "\n".join(logs.output))
        self.reload()
        self.assertIsNotNone(self.phone.revoked_at)

    def test_a_lost_start_confirmation_is_not_resent(self) -> None:
        with patch.object(inbound_service.replies, "reply_text", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.assertEqual(self.post("iniciar", sid=SID).status_code, 503)
        self.reload()
        self.assertIsNone(self.phone.revoked_at)

        self.post("iniciar", sid=SID)
        self.post("reanudar", sid=OTHER_SID)

        self.assert_nothing_sent_or_queued()

    def test_a_start_that_races_a_stop_is_applied_after_it(self) -> None:
        """The snapshot says not revoked; the STOP lands before the START is decided."""
        self.phone.clear_revocation()
        original = BenjiSmsPhone.newest_binding

        def stop_lands(self_phone: BenjiSmsPhone) -> Any:
            found = original(self_phone)
            BenjiSmsPhone.objects.get(pk=self_phone.pk).revoke()
            return found

        with patch.object(BenjiSmsPhone, "newest_binding", stop_lands):
            self.post("iniciar")

        self.reload()
        self.assertIsNone(self.phone.revoked_at)
        self.assertEqual(self.sent_bodies(), [replies.START_RESUMED.default])

    def test_a_replayed_carrier_start_does_not_undo_a_newer_stop(self) -> None:
        """Carrier keywords send nothing, so no delivery row could have caught this."""
        self.post("START", sid=SID)
        self.post("STOP", sid=OTHER_SID)

        self.post("START", sid=SID)

        self.reload()
        self.assertIsNotNone(self.phone.revoked_at)
        self.assert_nothing_sent_or_queued()

    def test_a_resuming_start_restarts_the_quiet_interval(self) -> None:
        """Resumed on its last quiet day, the conversation does not expire on the next text."""
        almost = timezone.now() - BENJI_SMS_QUIET_INTERVAL + timedelta(hours=1)
        BenjiSmsBinding.objects.update(last_inbound_at=almost)

        self.post("START")
        with patch.object(inbound_service.timezone, "now", return_value=timezone.now() + timedelta(hours=2)):
            self.post("what is snap", sid=OTHER_SID)

        self.enqueue_turn.assert_called_once_with(self.binding.conversation_id, OTHER_SID)
        self.reload()
        self.assertEqual(self.binding.status, AssistantConversationStatus.ACTIVE)

    def test_start_does_not_resume_a_conversation_the_stop_did_not_close(self) -> None:
        """Only the conversation the STOP ended comes back: not one an on-ramp superseded."""
        self.phone.clear_revocation()
        self.binding.end(AssistantConversationStatus.CLOSED)
        self.phone.revoke()

        self.post("START")

        self.reload()
        self.assertIsNone(self.phone.revoked_at)
        self.assertEqual(self.binding.status, AssistantConversationStatus.CLOSED)


@override_settings(**SETTINGS)
class KeywordFromAnActiveNumberTest(InboundMixin, TestCase):
    def test_a_carrier_help_sends_nothing(self) -> None:
        self.bind()
        for index, body in enumerate(["HELP", "info"]):
            self.assert_acknowledged(self.post(body, sid=f"SM{index:032x}"))
        self.assert_nothing_sent_or_queued()

    def test_a_help_wording_twilio_does_not_handle_gets_our_reply(self) -> None:
        binding = self.bind()

        self.post("¡Ayuda!")

        self.assertEqual(len(self.sent_bodies()), 1)
        self.assertIn(FRONTEND, self.sent_bodies()[0])
        self.assertEqual(BenjiSmsDelivery.objects.get().binding, binding)
        self.enqueue_turn.assert_not_called()

    def test_a_stop_landing_mid_request_stops_the_help_reply(self) -> None:
        self.bind()
        original = BenjiSmsPhone.newest_binding

        def stop_lands(self_phone: BenjiSmsPhone) -> Any:
            found = original(self_phone)
            BenjiSmsPhone.objects.get(pk=self_phone.pk).revoke()
            return found

        with patch.object(BenjiSmsPhone, "newest_binding", stop_lands):
            with self.assertLogs(LOGGER, level="INFO") as logs:
                self.assert_acknowledged(self.post("ayuda"))

        self.assert_nothing_sent_or_queued()
        self.assertIn("outcome=revoked", "\n".join(logs.output))

    def test_a_replayed_help_gets_one_reply(self) -> None:
        self.bind()
        self.post("ayuda")
        self.post("ayuda")

        self.assertEqual(self.create.call_count, 1)

    def test_start_with_nothing_to_clear_is_ignored(self) -> None:
        self.bind()
        for index, body in enumerate(["START", "unstop", "iniciar"]):
            self.assert_acknowledged(self.post(body, sid=f"SM{index:032x}"))
        self.assert_nothing_sent_or_queued()

    def test_yes_is_an_ordinary_answer(self) -> None:
        binding = self.bind()

        self.post("Yes")

        self.enqueue_turn.assert_called_once_with(binding.conversation_id, SID)


@override_settings(**SETTINGS)
class SharedTest(InboundMixin, TestCase):
    def test_a_shared_phone_gets_the_fixed_reply_once_a_day_and_no_turn(self) -> None:
        binding = self.bind()
        BenjiSmsPhone.objects.update(shared_until=timezone.now() + timedelta(days=5))

        self.assert_acknowledged(self.post())
        self.assert_acknowledged(self.post("which one?", sid=OTHER_SID))

        self.assertEqual(self.sent_bodies(), [replies.SHARED.default])
        self.assertEqual(BenjiSmsDelivery.objects.get().binding, binding)
        self.enqueue_turn.assert_not_called()

    def test_a_stop_landing_mid_request_stops_the_shared_reply(self) -> None:
        self.bind()
        BenjiSmsPhone.objects.update(shared_until=timezone.now() + timedelta(days=5))
        original = BenjiSmsPhone.is_shared

        def stop_lands(self_phone: BenjiSmsPhone, *args: Any) -> bool:
            BenjiSmsPhone.objects.get(pk=self_phone.pk).revoke()
            return original(self_phone, *args)

        with patch.object(BenjiSmsPhone, "is_shared", stop_lands):
            self.assert_acknowledged(self.post())

        self.assert_nothing_sent_or_queued()
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())

    def test_a_replay_after_the_mark_lapses_is_still_a_shared_reply(self) -> None:
        """Not a turn: the replay follows the first decision."""
        self.bind()
        BenjiSmsPhone.objects.update(shared_until=timezone.now() + timedelta(minutes=1))
        self.post()
        BenjiSmsPhone.objects.update(shared_until=timezone.now() - timedelta(minutes=1))

        self.post()

        self.enqueue_turn.assert_not_called()
        self.assertEqual(self.sent_bodies(), [replies.SHARED.default])

    def test_a_lapsed_mark_no_longer_applies(self) -> None:
        binding = self.bind()
        BenjiSmsPhone.objects.update(shared_until=timezone.now() - timedelta(minutes=1))

        self.post()

        self.create.assert_not_called()
        self.enqueue_turn.assert_called_once_with(binding.conversation_id, SID)


@override_settings(**SETTINGS)
class ExpiryTest(InboundMixin, TestCase):
    def assert_reentry(self, binding: BenjiSmsBinding, status: str) -> None:
        binding.refresh_from_db()
        binding.conversation.refresh_from_db()
        self.assertEqual(binding.status, status)
        self.assertEqual(binding.conversation.status, status)
        self.assertEqual(self.sent_bodies(), [replies.REENTRY.default])
        self.enqueue_turn.assert_not_called()

    def test_a_text_after_the_quiet_interval_expires_the_conversation(self) -> None:
        binding = self.bind(last_inbound_at=timezone.now() - BENJI_SMS_QUIET_INTERVAL - timedelta(hours=1))

        self.assert_acknowledged(self.post())

        self.assert_reentry(binding, AssistantConversationStatus.EXPIRED)

    def test_with_no_inbound_yet_the_interval_runs_from_the_on_ramp(self) -> None:
        binding = self.bind(created_at=timezone.now() - BENJI_SMS_QUIET_INTERVAL - timedelta(hours=1))

        self.post()

        self.assert_reentry(binding, AssistantConversationStatus.EXPIRED)

    def test_inside_the_interval_the_conversation_carries_on(self) -> None:
        binding = self.bind(last_inbound_at=timezone.now() - BENJI_SMS_QUIET_INTERVAL + timedelta(hours=1))

        self.post()

        self.create.assert_not_called()
        self.enqueue_turn.assert_called_once_with(binding.conversation_id, SID)

    def test_a_number_whose_conversation_already_ended_gets_the_reentry_reply(self) -> None:
        for status in (AssistantConversationStatus.EXPIRED, AssistantConversationStatus.CLOSED):
            with self.subTest(status=status):
                self.create.reset_mock()
                BenjiSmsStrangerReply.objects.all().delete()
                BenjiSmsDelivery.objects.all().delete()
                BenjiSmsBinding.objects.all().delete()
                binding = self.bind()
                binding.end(status)

                self.post()

                self.assert_reentry(binding, status)

    def test_a_stop_landing_mid_request_stops_the_reentry_reply(self) -> None:
        self.bind().end(AssistantConversationStatus.EXPIRED)
        original = BenjiSmsPhone.newest_binding

        def stop_lands(self_phone: BenjiSmsPhone) -> Any:
            found = original(self_phone)
            BenjiSmsPhone.objects.get(pk=self_phone.pk).revoke()
            return found

        with patch.object(BenjiSmsPhone, "newest_binding", stop_lands):
            self.assert_acknowledged(self.post())

        self.assert_nothing_sent_or_queued()

    def test_the_reentry_reply_goes_out_once_a_day(self) -> None:
        self.bind().end(AssistantConversationStatus.EXPIRED)

        self.post()
        self.post("hello?", sid=OTHER_SID)

        self.assertEqual(self.create.call_count, 1)

    def test_a_replay_of_the_expiring_text_sends_nothing_new(self) -> None:
        self.bind(last_inbound_at=timezone.now() - BENJI_SMS_QUIET_INTERVAL - timedelta(hours=1))

        self.post()
        self.post()

        self.assertEqual(self.create.call_count, 1)


@override_settings(**SETTINGS)
class TurnTest(InboundMixin, TestCase):
    def test_an_ordinary_text_queues_the_turn_and_sends_nothing(self) -> None:
        binding = self.bind()

        self.assert_acknowledged(self.post("what is snap"))

        self.enqueue_turn.assert_called_once_with(binding.conversation_id, SID)
        self.create.assert_not_called()
        self.enqueue_media_deletion.assert_not_called()
        self.assertFalse(BenjiSmsDelivery.objects.exists())

    def test_it_records_the_inbound_time(self) -> None:
        binding = self.bind()
        self.assertIsNone(binding.last_inbound_at)

        self.post()

        binding.refresh_from_db()
        self.assertIsNotNone(binding.last_inbound_at)

    def test_a_replay_after_a_new_on_ramp_queues_in_the_first_conversation(self) -> None:
        """The worker deduplicates by SID within a conversation, so the turn stays there."""
        first = self.bind()
        self.post()
        first.end(AssistantConversationStatus.CLOSED)
        self.bind()

        self.post()

        self.assertEqual(
            [call.args for call in self.enqueue_turn.call_args_list],
            [(first.conversation_id, SID), (first.conversation_id, SID)],
        )

    def test_a_turn_that_could_not_be_queued_is_queued_on_the_replay(self) -> None:
        binding = self.bind()
        self.enqueue_turn.side_effect = BrokerNotConfigured("no broker")
        with self.assertLogs(LOGGER, level="WARNING"):
            self.assertEqual(self.post().status_code, 503)
        self.assertEqual(self.enqueue_turn.call_count, 1)
        self.enqueue_turn.side_effect = None

        self.assert_acknowledged(self.post())

        self.assertEqual([call.args for call in self.enqueue_turn.call_args_list], [(binding.conversation_id, SID)] * 2)

    def test_a_replayed_turn_is_not_queued_once_its_white_label_is_switched_off(self) -> None:
        self.bind()
        self.enqueue_turn.side_effect = BrokerNotConfigured("no broker")
        with self.assertLogs(LOGGER, level="WARNING"):
            self.post()
        self.enqueue_turn.side_effect = None
        self.white_label.feature_flags = {benji_sms.FLAG: False}
        self.white_label.save()

        self.post()

        self.assertEqual(self.enqueue_turn.call_count, 1)

    def test_a_replayed_turn_is_not_queued_after_a_stop(self) -> None:
        binding = self.bind()
        self.post()
        self.post("alto", sid=OTHER_SID)

        self.post()

        self.assertEqual(self.enqueue_turn.call_count, 1)
        binding.phone.refresh_from_db()
        self.assertIsNotNone(binding.phone.revoked_at)

    def test_a_replayed_turn_is_queued_again_for_the_worker_to_absorb(self) -> None:
        """The worker dedupes on the SID (client_message_id, MFB-2440); nothing is sent here."""
        self.bind()
        self.post()
        self.post()

        self.assertEqual(self.enqueue_turn.call_count, 2)
        self.create.assert_not_called()

    def test_with_the_flag_off_no_turn_is_queued(self) -> None:
        binding = self.bind()
        self.white_label.feature_flags = {benji_sms.FLAG: False}
        self.white_label.save()

        self.assert_acknowledged(self.post())

        self.assert_nothing_sent_or_queued()
        binding.refresh_from_db()
        self.assertIsNone(binding.last_inbound_at)

    def test_a_replayed_text_from_while_the_flag_was_off_stays_unanswered(self) -> None:
        binding = self.bind()
        self.white_label.feature_flags = {benji_sms.FLAG: False}
        self.white_label.save()
        self.post()
        self.white_label.feature_flags = {benji_sms.FLAG: True}
        self.white_label.save()

        self.post()

        self.assert_nothing_sent_or_queued()
        binding.refresh_from_db()
        self.assertIsNone(binding.last_inbound_at)

    def test_with_the_kill_switch_off_no_turn_is_queued(self) -> None:
        self.bind()

        with override_settings(BENJI_SMS_OUTBOUND_ENABLED=""):
            self.assert_acknowledged(self.post())

        self.assert_nothing_sent_or_queued()

    def test_debug_alone_does_not_stop_a_turn(self) -> None:
        """Local work runs the turn end to end; only the send is refused in DEBUG."""
        binding = self.bind()

        with override_settings(DEBUG=True):
            self.post()

        self.enqueue_turn.assert_called_once_with(binding.conversation_id, SID)

    def test_a_text_racing_a_stop_from_the_same_number_is_not_answered(self) -> None:
        """The STOP closed the binding between the routing read and the locked write."""
        binding = self.bind()
        original = BenjiSmsBinding.record_inbound

        def stop_lands_first(self_binding: BenjiSmsBinding, *args: Any, **kwargs: Any) -> bool:
            binding.phone.revoke()
            return original(self_binding, *args, **kwargs)

        with patch.object(BenjiSmsBinding, "record_inbound", stop_lands_first):
            self.assert_acknowledged(self.post())

        self.assert_nothing_sent_or_queued()
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())

    def test_an_empty_text_is_not_a_turn(self) -> None:
        self.bind()

        self.assert_acknowledged(self.post("   "))

        self.assert_nothing_sent_or_queued()

    def test_a_turn_that_cannot_be_queued_is_a_503_so_twilio_posts_again(self) -> None:
        self.bind()
        self.enqueue_turn.side_effect = BrokerNotConfigured("no broker")

        with self.assertLogs(LOGGER, level="WARNING") as logs:
            response = self.post("my case number is 12345")

        self.assertEqual(response.status_code, 503)
        self.assertIn("BrokerNotConfigured", logs.output[0])
        self.assertNotIn("12345", "".join(logs.output))


@override_settings(**SETTINGS)
class PictureTest(InboundMixin, TestCase):
    def test_a_picture_gets_the_fixed_reply_and_its_media_deleted(self) -> None:
        binding = self.bind()

        self.assert_acknowledged(self.post("see this", media=2, sid="MM" + "c3" * 16))

        self.assertEqual(self.sent_bodies(), [replies.PICTURE.default])
        self.enqueue_media_deletion.assert_called_once_with("MM" + "c3" * 16, binding.conversation_id)
        self.enqueue_turn.assert_not_called()
        self.assertEqual(BenjiSmsDelivery.objects.get().binding, binding)
        binding.refresh_from_db()
        self.assertIsNotNone(binding.last_inbound_at)

    def test_a_stop_landing_after_the_text_is_recorded_stops_the_picture_reply(self) -> None:
        binding = self.bind()
        original = BenjiSmsBinding.record_inbound

        def then_stop(self_binding: BenjiSmsBinding, *args: Any, **kwargs: Any) -> bool:
            kept = original(self_binding, *args, **kwargs)
            binding.phone.revoke()
            return kept

        with patch.object(BenjiSmsBinding, "record_inbound", then_stop):
            self.assert_acknowledged(self.post("", media=1))

        self.create.assert_not_called()
        self.enqueue_media_deletion.assert_called_once()

    def test_a_handled_text_whose_media_cannot_be_queued_still_logs_its_outcome(self) -> None:
        self.bind()
        self.enqueue_media_deletion.side_effect = BrokerNotConfigured("no broker")

        with self.assertLogs(LOGGER, level="INFO") as logs:
            response = self.post("", media=1)

        self.assertEqual(response.status_code, 503)
        output = "\n".join(logs.output)
        self.assertIn("outcome=picture replied=True", output)
        self.assertIn("media deletion not queued", output)
        self.assertIn("BrokerNotConfigured", output)

    def test_media_is_queued_for_deletion_even_when_the_binding_cannot_be_read(self) -> None:
        self.bind()
        with patch.object(BenjiSmsPhone, "newest_binding", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.assertEqual(self.post("", media=1).status_code, 503)

        self.enqueue_media_deletion.assert_called_once_with(SID, None)

    def test_media_is_queued_for_deletion_even_when_the_number_cannot_be_hashed(self) -> None:
        with override_settings(BENJI_SMS_HASH_KEY=""):
            with self.assertLogs(LOGGER, level="WARNING"):
                response = self.post("", media=1)

        self.assertEqual(response.status_code, 503)
        self.enqueue_media_deletion.assert_called_once_with(SID, None)
        self.create.assert_not_called()

    def test_a_picture_reply_retried_on_replay_stays_with_its_conversation(self) -> None:
        first = self.bind()
        with patch.object(inbound_service.replies, "reply_text", side_effect=RuntimeError("db gone")):
            with self.assertLogs(LOGGER, level="WARNING"):
                self.post("", media=1)
        first.end(AssistantConversationStatus.CLOSED)
        self.bind()

        self.post("", media=1)

        self.assertEqual(self.sent_bodies(), [replies.PICTURE.default])
        self.assertEqual(BenjiSmsDelivery.objects.get().binding, first)

    def test_a_replayed_picture_gets_one_reply(self) -> None:
        self.bind()
        self.post("", media=1)
        self.post("", media=1)

        self.assertEqual(self.create.call_count, 1)
        # Deleting twice is harmless, and the first job may have failed.
        self.assertEqual(self.enqueue_media_deletion.call_count, 2)

    def test_a_strangers_picture_is_deleted_too(self) -> None:
        self.post("", media=1)

        self.enqueue_media_deletion.assert_called_once_with(SID, None)
        self.assertEqual(len(self.sent_bodies()), 1)
        self.assertIn("MyFriendBen", self.sent_bodies()[0])

    def test_media_is_deleted_whatever_state_the_number_is_in(self) -> None:
        binding = self.bind()
        binding.phone.revoke()

        self.post("", media=1)

        self.enqueue_media_deletion.assert_called_once_with(SID, binding.conversation_id)
        self.create.assert_not_called()

    def test_media_from_a_sender_that_is_not_a_phone_is_deleted(self) -> None:
        self.post("", media=1, sender="12345")

        self.enqueue_media_deletion.assert_called_once_with(SID, None)

    def test_a_deletion_that_cannot_be_queued_is_a_503_and_the_replay_only_retries_it(self) -> None:
        self.enqueue_media_deletion.side_effect = BrokerNotConfigured("no broker")

        with self.assertLogs(LOGGER, level="WARNING"):
            response = self.post("", media=1)

        self.assertEqual(response.status_code, 503)
        # The text was handled before the deletion failed: the stranger got the reply.
        self.create.assert_called_once()

        self.enqueue_media_deletion.side_effect = None
        self.assert_acknowledged(self.post("", media=1))
        self.create.assert_called_once()
        self.assertEqual(self.enqueue_media_deletion.call_count, 2)


@override_settings(**SETTINGS)
class FallbackTest(InboundMixin, TestCase):
    def test_the_fallback_url_handles_the_text_and_logs_twilios_error(self) -> None:
        binding = self.bind()

        with self.assertLogs(LOGGER, level="WARNING") as logs:
            response = self.post(path=FALLBACK_PATH, extra={"ErrorCode": "11200", "ErrorUrl": ORIGIN + INBOUND_PATH})

        self.assert_acknowledged(response)
        self.enqueue_turn.assert_called_once_with(binding.conversation_id, SID)
        self.assertIn("twilio_error=11200", logs.output[0])

    def test_a_text_the_primary_url_already_answered_gets_nothing_more(self) -> None:
        self.post()
        with self.assertLogs(LOGGER, level="WARNING"):
            self.post(path=FALLBACK_PATH, extra={"ErrorCode": "11200"})

        self.create.assert_called_once()


@override_settings(**SETTINGS)
class LocaleAndLogTest(InboundMixin, TestCase):
    def test_a_reply_uses_the_conversations_language_when_a_translation_exists(self) -> None:
        from translations.models import Translation

        translation = Translation.objects.add_translation(replies.PICTURE.label, "English picture reply")
        translation.set_current_language("es")
        translation.text = "Benji todavía no puede leer fotos."
        translation.save()
        self.bind(
            conversation=make_conversation(white_label=self.white_label.code, channel=AssistantChannel.SMS, locale="es")
        )

        self.post("", media=1)

        self.assertEqual(self.sent_bodies(), ["Benji todavía no puede leer fotos."])

    def test_the_twilio_sdk_does_not_log_request_urls(self) -> None:
        """Its URLs carry the MessageSid, and the worker logs INFO."""
        import logging

        self.assertFalse(logging.getLogger("twilio.http_client").isEnabledFor(logging.INFO))

    def test_the_outcome_line_reaches_the_logs_at_info(self) -> None:
        """settings.LOGGING names this module's logger; without it, INFO goes nowhere."""
        import logging

        from screener import benji_sms_inbound as view_module

        configured = logging.getLogger(view_module.__name__)
        self.assertTrue(configured.handlers)
        self.assertEqual(configured.level, logging.INFO)

    def test_nothing_logged_carries_the_number_its_hash_or_the_text(self) -> None:
        self.bind()
        secret = "my ssn is 078-05-1120"
        with self.assertLogs(level="DEBUG") as logs:
            self.post(secret)
            self.post("alto", sid=OTHER_SID)
            self.post("hi", sender=OTHER_PHONE, sid="SM" + "d4" * 16)

        output = "\n".join(logs.output)
        for leaked in (PHONE, PHONE[2:], OTHER_PHONE, phone_hash(PHONE), phone_hash(OTHER_PHONE), "078-05-1120"):
            self.assertNotIn(leaked, output)
        self.assertIn("outcome=queued", output)
        self.assertIn("outcome=stopped", output)
        self.assertIn("outcome=stranger", output)


@override_settings(**SETTINGS)
class ConcurrentReplayTest(InboundMixin, TransactionTestCase):
    """Texts posted at the same moment: the database lets exactly one reply or change out."""

    def _race(self, claim: Any) -> list[Any]:
        """Run `claim` in two threads released together. Fails the test, rather than
        returning partial results, if either thread raised or has not finished."""
        barrier = threading.Barrier(2)
        results: list[Any] = []
        errors: list[BaseException] = []

        def run() -> None:
            try:
                # Bound any lock wait, so a stuck claim fails here instead of outliving
                # the test while holding a connection.
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                barrier.wait(timeout=5)
                results.append(claim())
            except BaseException as exc:
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse([thread for thread in threads if thread.is_alive()], "a claim thread did not finish")
        if errors:
            raise errors[0]
        return results

    def test_one_inbound_sid_claims_one_fixed_reply(self) -> None:
        results = self._race(lambda: BenjiSmsDelivery.objects.claim_fixed(SID))

        self.assertEqual(len(results), 2)
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(BenjiSmsDelivery.objects.count(), 1)

    def test_two_stops_at_once_send_one_confirmation(self) -> None:
        """Only the STOP that makes the change confirms it; the phone row lock decides which."""
        binding = self.bind()
        sids = iter(["SM" + "c1" * 16, "SM" + "c2" * 16])
        sids_lock = threading.Lock()

        def confirm() -> bool:
            with sids_lock:
                inbound_sid = next(sids)
            inbound = inbound_service.Inbound(sid=inbound_sid, sender=PHONE, body="alto", num_media=0)
            return inbound_service.handle_inbound(inbound).replied

        results = self._race(confirm)

        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.create.call_count, 1)

    def test_two_posts_of_one_yes_at_once_queue_no_turn(self) -> None:
        """A revoked number's "yes", posted twice together: one clears, neither is a turn."""
        binding = self.bind()
        binding.phone.revoke()

        def post_yes() -> str:
            inbound = inbound_service.Inbound(sid=SID, sender=PHONE, body="yes", num_media=0)
            return inbound_service.handle_inbound(inbound).outcome.value

        results = self._race(post_yes)

        self.assertEqual(sorted(results), ["started", "started"])
        self.enqueue_turn.assert_not_called()
        binding.phone.refresh_from_db()
        self.assertIsNone(binding.phone.revoked_at)

    def test_one_number_claims_one_reply_a_day(self) -> None:
        number_hash = phone_hash(PHONE)

        results = self._race(lambda: BenjiSmsStrangerReply.objects.claim(number_hash))

        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(BenjiSmsStrangerReply.objects.count(), 1)
