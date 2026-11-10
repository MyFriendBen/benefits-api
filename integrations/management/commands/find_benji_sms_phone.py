"""Find a phone's Benji SMS rows by its number, for support and deletion requests.

The admin cannot search by phone hash or number: admin search is a GET, so the term
would land in the URL, the router logs and Sentry's request data (see screener/admin.py).
This reads the number from a hidden prompt instead, so it is not in the shell history,
the process list or the dyno's log either, hashes it, and prints row ids only:

    heroku run python manage.py find_benji_sms_phone

Prints the phone row and each binding with its conversation, so a deletion request can
be served by deleting those conversations (bindings and deliveries cascade) and then the
phone row. It never prints the number or the hash, and changes nothing.
"""

import getpass
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from integrations.services.communications.benji_sms_hash import InvalidPhoneNumber, phone_hash
from screener.models import BenjiSmsPhone, BenjiSmsStrangerReply

PROMPT = "Phone number (hidden): "


class Command(BaseCommand):
    help = "Look up a phone's Benji SMS rows by its number, read from a hidden prompt. Read-only."

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            hashed = phone_hash(getpass.getpass(PROMPT))
        except InvalidPhoneNumber:
            raise CommandError("That is not a phone number.") from None

        phone = BenjiSmsPhone.objects.filter(phone_hash=hashed).first()
        stranger = BenjiSmsStrangerReply.objects.filter(phone_hash=hashed).exists()
        if phone is None:
            self.stdout.write("No Benji SMS phone row for that number.")
            if stranger:
                self.stdout.write("It has a stranger-reply row (purged after a day).")
            return

        self.stdout.write(
            f"Phone {phone.pk}: revoked_at={phone.revoked_at} shared_until={phone.shared_until} "
            f"created_at={phone.created_at}"
        )
        bindings = phone.bindings.select_related("conversation").order_by("-created_at")
        if not bindings:
            self.stdout.write("  No bindings.")
        for binding in bindings:
            self.stdout.write(
                f"  Binding {binding.pk} ({binding.status}): conversation {binding.conversation_id}, "
                f"screen {binding.conversation.screen_uuid}, created_at={binding.created_at}"
            )
        if stranger:
            self.stdout.write("It also has a stranger-reply row (purged after a day).")
