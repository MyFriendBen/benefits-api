from django.core.management.base import BaseCommand
from screener import webhooks
import argparse
from sys import stdin

from screener.models import Screen
from screener.views import all_results


class Command(BaseCommand):
    help = "Retrigger webhook for a list of screen uuids"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "uuids",
            nargs="?",
            type=argparse.FileType("r", encoding="utf-8"),
            default=stdin,
        )

    def handle(self, *args, **options) -> None:
        uuids = []
        while line := options["uuids"].readline():
            line = line.strip()

            if line.startswith("#"):
                continue
            if line == "":
                continue

            uuids.append(line)

        for uuid in uuids:
            screen: Screen = Screen.objects.prefetch_related(
                "household_members",
                "household_members__income_streams",
                "household_members__insurance",
                "household_members__energy_calculator",
                "expenses",
                "energy_calculator",
            ).get(uuid=uuid)

            try:
                results = all_results(screen, True)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to calculate eligibility for '{screen.uuid}'. Failed with error: '{repr(e)}'"
                    )
                )
                continue

            webhook = webhooks.get_web_hook(screen)

            if webhook is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"No webhhook for '{screen.uuid}'. There is no webhook for the referrer '{screen.referrer_code}'"
                    )
                )
                continue

            err = webhook.send(screen, results, force=True)

            if err is not None:
                self.stdout.write(
                    self.style.ERROR(f"Failed to trigger webhook for '{screen.uuid}'. Failed with error: '{repr(err)}'")
                )
            else:
                self.stdout.write(self.style.SUCCESS(f"Webhook triggered for '{screen.uuid}'"))
