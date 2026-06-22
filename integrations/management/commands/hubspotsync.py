from django.core.management.base import BaseCommand
from authentication.models import User
from integrations.services.cms_integration import CoHubSpotIntegration
from screener.models import Screen
from django.db.models import Q
import time


class Command(BaseCommand):
    help = "Syncs new users to Hubspot and clears PII from local records"

    def add_arguments(self, parser) -> None:
        parser.add_argument("limit", nargs="?", default="1", type=int)

    def handle(self, *args, **options) -> None:
        limit = options["limit"]
        status = self.sync_mfb_hubspot_users(limit)
        if len(status["completed"]) > 0:
            self.stdout.write(self.style.SUCCESS("Successfully synced %s users." % len(status["completed"])))
            for message in status["completed"]:
                self.stdout.write(
                    self.style.SUCCESS("Successfully synced user %s with contact %s." % (message[0], message[1]))
                )
        if len(status["failed"]) > 0:
            self.stdout.write(self.style.WARNING("Failed to sync %s users." % len(status["failed"])))
            for message in status["failed"]:
                self.stdout.write(
                    self.style.SUCCESS("Successfully synced user %s with contact %s." % (message[0], message[1]))
                )

    # MFB allows users to sign up to receive benefits updates or offers. If they do
    # so PII is temporarily stored against their user record. This cron function
    # queries the database every 10 minutes for new signups, syncs that data to
    # hubspot, and then clears the PII on the user record in favor of storing the
    # external id. This separates PII from household demographic.
    def sync_mfb_hubspot_users(self, limit: int):
        status = {"processed": 0, "completed": [], "failed": []}
        screen = None
        processed = 0

        # for now, we only sync users to hubspot who have signed up for offers or
        # updates and given TCPA consent
        unsynced = (
            User.objects.filter(Q(send_offers=True) | Q(send_updates=True))
            .filter(external_id__isnull=True)
            .filter(Q(tcpa_consent=True) | Q(explicit_tcpa_consent=True))
        )

        for user in unsynced:
            if processed < limit:
                user_screens = Screen.objects.filter(user_id=user.id, white_labels__code="co").order_by(
                    "-submission_date"
                )
                if user_screens:
                    screen = user_screens.first()
                else:
                    continue

                try:
                    hubspot = CoHubSpotIntegration(user, screen)
                    hubspot_id = hubspot.add()
                    user.anonomize(hubspot_id)
                    status["completed"].append((user.id, hubspot_id))
                except Exception:
                    status["failed"].append((user.id, hubspot_id))

            # Delay to prevent hitting rate limit of 100 req per 10 seconds
            time.sleep(0.2)
            processed += 1
        return status
