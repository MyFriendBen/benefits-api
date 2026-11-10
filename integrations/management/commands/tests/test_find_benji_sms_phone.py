"""find_benji_sms_phone: look up a phone's rows by number, without the number leaking."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from integrations.services.communications.benji_sms_hash import phone_hash
from screener.models import AssistantChannel, BenjiSmsBinding, BenjiSmsPhone, BenjiSmsStrangerReply, WhiteLabel
from screener.tests.assistant_helpers import make_conversation

NUMBER = "+13035550100"
TYPED = "(303) 555-0100"


@override_settings(BENJI_SMS_HASH_KEY="k" * 64)
class FindBenjiSmsPhoneTest(TestCase):
    def run_cmd(self, typed: str = TYPED) -> str:
        out = StringIO()
        with patch("integrations.management.commands.find_benji_sms_phone.getpass.getpass", return_value=typed):
            call_command("find_benji_sms_phone", stdout=out)
        return out.getvalue()

    def test_prints_the_phone_and_each_binding_with_its_conversation(self) -> None:
        phone = BenjiSmsPhone.objects.create(phone_hash=phone_hash(NUMBER))
        white_label = WhiteLabel.objects.create(name="Test", code="test_sms", state_code="TS")
        conversation = make_conversation(white_label=white_label.code, channel=AssistantChannel.SMS)
        binding = BenjiSmsBinding.objects.create(
            phone=phone,
            white_label=white_label,
            conversation=conversation,
            consented_at=timezone.now(),
            consent_version="benji.sms.consent-v1",
        )

        output = self.run_cmd()

        self.assertIn(f"Phone {phone.pk}", output)
        self.assertIn(f"Binding {binding.pk} (active)", output)
        self.assertIn(str(conversation.conversation_id), output)

    def test_never_prints_the_number_or_the_hash(self) -> None:
        hashed = phone_hash(NUMBER)
        BenjiSmsPhone.objects.create(phone_hash=hashed)
        BenjiSmsStrangerReply.objects.create(phone_hash=hashed)

        output = self.run_cmd()

        for secret in (NUMBER, TYPED, "3035550100", hashed):
            self.assertNotIn(secret, output)

    def test_reports_an_unknown_number(self) -> None:
        self.assertIn("No Benji SMS phone row", self.run_cmd())

    def test_reports_a_stranger_only_number(self) -> None:
        BenjiSmsStrangerReply.objects.create(phone_hash=phone_hash(NUMBER))

        output = self.run_cmd()

        self.assertIn("No Benji SMS phone row", output)
        self.assertIn("stranger-reply row", output)

    def test_refuses_input_that_is_not_a_number_without_echoing_it(self) -> None:
        with self.assertRaises(CommandError) as caught:
            self.run_cmd("555-0100")

        self.assertNotIn("555-0100", str(caught.exception))
