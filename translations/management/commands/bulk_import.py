from django.core.management.base import BaseCommand
from translations.bulk_import_translations import bulk_add
from sys import stdin
import argparse
import json


class Command(BaseCommand):
    """
    Run on heroku:
    `heroku run --no-tty -a [HEROKU APP NAME] manage.py bulk_import < [PATH TO FILE]`
    """

    help = """
    Get translation export
    """

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "data",
            nargs="?",
            type=argparse.FileType("r", encoding="utf-8"),
            default=stdin,
        )

    def handle(self, *args, **options) -> None:
        data = json.load(options["data"])

        bulk_add(data)
