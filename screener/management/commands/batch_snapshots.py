from django.core.management.base import BaseCommand
from screener.models import Screen
from screener.views import eligibility_results
from tqdm import trange
import time


class Command(BaseCommand):
    help = """
    Creates snapshots for all users.
    Limit default is 1.
    Defaults to only creating snapshots for users with emails.
    """

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", default=1, type=int)
        parser.add_argument("--all", default=False, type=bool)
        parser.add_argument("--new", default=False, type=bool)
        parser.add_argument("--white-label", default="co", type=str)

    def handle(self, *args, **options) -> None:
        # Get the screens
        screens = Screen.objects.filter(agree_to_tos=True, is_test=False, is_test_data=False, completed=True)

        if not options["all"]:
            screens = screens.exclude(user__isnull=True)

        if options["new"]:
            screens = screens.filter(eligibility_snapshots__isnull=True)

        if options["white_label"]:
            screens = screens.filter(white_label__code=options["white_label"])

        # List[:None] is everything in the list
        limit = None if options["limit"] == -1 else options["limit"]
        screens = screens.order_by("-submission_date")[:limit]

        # Calculate eligibility for each screen
        errors = []
        for i in trange(len(screens), desc="Screens"):
            try:
                eligibility_results(screens[i], batch=True)
                time.sleep(1)
            except Exception as e:
                errors.append(str(screens[i].id) + ": " + str(e))
        if len(errors):
            self.stdout.write(self.style.ERROR("The following screens had errors:\n" + "\n".join(errors)))
