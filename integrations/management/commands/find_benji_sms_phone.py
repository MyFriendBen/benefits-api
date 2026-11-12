"""Find a phone's Benji SMS rows by its number, and serve a deletion request.

The admin cannot search by phone hash or number: admin search is a GET, so the term
would land in the URL, the router logs and Sentry's request data (see screener/admin.py).
This reads the number from a hidden prompt instead, so it is not in the shell history,
the process list or the dyno's log either, and prints row ids only:

    heroku run python manage.py find_benji_sms_phone            # look up, read-only
    heroku run python manage.py find_benji_sms_phone --delete   # "remove my texts"

With --delete it lists what it found, asks for the word DELETE, and then runs
`BenjiSmsPhone.delete_with_conversations()`: the phone's SMS conversations (messages,
bindings and deliveries cascade), its stranger row, then the phone row, in one
transaction. Web conversations on the same screens are not touched. It never prints the
number or the hash.
"""

import getpass
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from integrations.services.communications.benji_sms_hash import InvalidPhoneNumber
from screener.models import BenjiSmsPhone, BenjiSmsStrangerReply

PROMPT = "Phone number (hidden): "
CONFIRM_WORD = "DELETE"


class Command(BaseCommand):
    help = "Look up a phone's Benji SMS rows by a number read from a hidden prompt; --delete serves a deletion request."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete the phone's SMS conversations, stranger row and phone row, after confirmation.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        number = getpass.getpass(PROMPT)
        try:
            phone = BenjiSmsPhone.objects.for_number(number)
            stranger = BenjiSmsStrangerReply.objects.for_number(number)
        except InvalidPhoneNumber:
            raise CommandError("That is not a phone number.") from None

        if phone is None:
            self.stdout.write("No Benji SMS phone row for that number.")
            if stranger.exists():
                self.stdout.write("It has a stranger-reply row (purged after a day).")
                if options["delete"] and self._confirmed("the stranger-reply row"):
                    stranger.delete()
                    self.stdout.write("Deleted the stranger-reply row.")
            return

        self.stdout.write(
            f"Phone {phone.pk}: revoked_at={phone.revoked_at} shared_until={phone.shared_until} "
            f"created_at={phone.created_at}"
        )
        bindings = list(phone.bindings.select_related("conversation").order_by("-created_at"))
        if not bindings:
            self.stdout.write("  No bindings.")
        for binding in bindings:
            self.stdout.write(
                f"  Binding {binding.pk} ({binding.status}): conversation {binding.conversation_id}, "
                f"screen {binding.conversation.screen_uuid}, created_at={binding.created_at}"
            )
        if stranger.exists():
            self.stdout.write("It also has a stranger-reply row (purged after a day).")

        if not options["delete"]:
            return
        conversations = len({binding.conversation_id for binding in bindings})
        if not self._confirmed(
            f"{conversations} SMS conversation(s), their bindings and deliveries, and the phone row"
        ):
            self.stdout.write("Nothing deleted.")
            return
        deleted = phone.delete_with_conversations()
        self.stdout.write(f"Deleted {deleted} SMS conversation(s) and the phone row.")

    def _confirmed(self, what: str) -> bool:
        answer = input(f"This permanently deletes {what}. Type {CONFIRM_WORD} to continue: ")
        return answer.strip() == CONFIRM_WORD
