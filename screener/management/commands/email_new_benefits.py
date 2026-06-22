from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from integrations.services.cms_integration import CoHubSpotIntegration
from screener.models import Screen, EligibilitySnapshot


class Command(BaseCommand):
    help = """
    Update number of new benefits and amount of new benefits in HubSpot
    """

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", default=1, type=int)
        parser.add_argument("--white-label", default="co", type=str)

    def handle(self, *args, **options) -> None:
        screens = Screen.objects.all().exclude(user__isnull=True, white_label__code=options["white_label"])
        latest_snapshots = []
        limit = options["limit"]
        for screen in screens:
            try:
                previous_snapshot = EligibilitySnapshot.objects.filter(is_batch=True, screen=screen).latest(
                    "submission_date"
                )
            except ObjectDoesNotExist:
                self.stdout.write(self.style.WARNING(f"No snapshots for screen with id of {screen.id}"))
                continue
            latest_snapshots.append(previous_snapshot)

        existing_users = []
        for snapshot in latest_snapshots:
            if limit == 0:
                break
            if snapshot.screen.user is None or snapshot.screen.user.external_id is None:
                continue

            num_eligible = 0
            value = 0
            for program in snapshot.program_snapshots.all():
                if program.new and program.eligible:
                    num_eligible += 1
                    value += program.estimated_value

            existing_users.append(
                CoHubSpotIntegration.format_email_new_benefit(snapshot.screen.user.external_id, num_eligible, value)
            )

            limit -= 1

        if not len(existing_users):
            self.stdout.write(self.style.WARNING("No users in HubSpot. Make sure that you add users to HubSpot first"))
            return

        CoHubSpotIntegration.bulk_update(existing_users)
