from django.core.management.base import BaseCommand
from translations.models import Translation
from django.conf import settings
from sys import stdin
import argparse
import json


class Command(BaseCommand):
    help = "Add translation label records from a JSON file."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "data",
            nargs="?",
            type=argparse.FileType("r", encoding="utf-8"),
            default=stdin,
        )

    def handle(self, *args, **options) -> None:
        data = json.load(options["data"])

        for label, details in data.items():
            translation = Translation.objects.add_translation(
                label,
                details["langs"].get(settings.LANGUAGE_CODE, ["", False])[0],
                active=details["active"],
                no_auto=details["no_auto"],
            )

            for lang, message in details["langs"].items():
                Translation.objects.edit_translation_by_id(translation.id, lang, message[0], manual=message[1])

        self.stdout.write(self.style.SUCCESS("Successfully added translations."))
