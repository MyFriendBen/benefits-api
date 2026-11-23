"""find_benji_sms_phone: look up a phone's rows by number, without the number leaking."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from integrations.services.communications.benji_sms_hash import phone_hash
from screener.models import (
    AssistantChannel,
    AssistantConversation,
    BenjiSmsBinding,
    BenjiSmsPhone,
    BenjiSmsStrangerReply,
    WhiteLabel,
)
from screener.tests.assistant_helpers import make_conversation

NUMBER = "+13035550100"
TYPED = "(303) 555-0100"


@override_settings(BENJI_SMS_HASH_KEY="k" * 64)
class FindBenjiSmsPhoneTest(TestCase):
    def run_cmd(self, typed: str = TYPED, *args: str, confirm: str = "") -> str:
        out = StringIO()
        module = "integrations.management.commands.find_benji_sms_phone"
        with patch(f"{module}.getpass.getpass", return_value=typed), patch("builtins.input", return_value=confirm):
            call_command("find_benji_sms_phone", *args, stdout=out)
        return out.getvalue()

    def make_bound_phone(self) -> BenjiSmsPhone:
        phone = BenjiSmsPhone.objects.create(phone_hash=phone_hash(NUMBER))
        white_label = WhiteLabel.objects.create(name="Test", code="test_sms", state_code="TS")
        BenjiSmsBinding.objects.create(
            phone=phone,
            white_label=white_label,
            conversation=make_conversation(white_label=white_label.code, channel=AssistantChannel.SMS),
            consented_at=timezone.now(),
            consent_version="benji.sms.consent-v1",
        )
        return phone

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

    def test_delete_removes_everything_after_confirmation(self) -> None:
        phone = self.make_bound_phone()
        BenjiSmsStrangerReply.objects.create(phone_hash=phone.phone_hash)

        output = self.run_cmd(TYPED, "--delete", confirm="DELETE")

        self.assertIn("Deleted 1 SMS conversation(s) and the phone row.", output)
        self.assertFalse(BenjiSmsPhone.objects.exists())
        self.assertFalse(BenjiSmsBinding.objects.exists())
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())
        self.assertFalse(AssistantConversation.objects.exists())

    def test_delete_without_the_confirmation_word_deletes_nothing(self) -> None:
        self.make_bound_phone()

        output = self.run_cmd(TYPED, "--delete", confirm="yes")

        self.assertIn("Nothing deleted.", output)
        self.assertEqual(BenjiSmsPhone.objects.count(), 1)
        self.assertEqual(AssistantConversation.objects.count(), 1)

    def test_lookup_alone_never_asks_or_deletes(self) -> None:
        self.make_bound_phone()

        with patch("builtins.input", side_effect=AssertionError("asked for confirmation")):
            out = StringIO()
            with patch("integrations.management.commands.find_benji_sms_phone.getpass.getpass", return_value=TYPED):
                call_command("find_benji_sms_phone", stdout=out)

        self.assertEqual(BenjiSmsPhone.objects.count(), 1)

    def test_delete_of_a_stranger_only_number(self) -> None:
        BenjiSmsStrangerReply.objects.create(phone_hash=phone_hash(NUMBER))

        output = self.run_cmd(TYPED, "--delete", confirm="DELETE")

        self.assertIn("Deleted the stranger-reply row.", output)
        self.assertFalse(BenjiSmsStrangerReply.objects.exists())
