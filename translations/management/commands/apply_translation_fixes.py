"""
Django management command that overwrites specific translations from a CSV
(label, lang, prod_text, staging_text), e.g. to copy staging's corrected
strings onto an environment that still has renamed or dropped placeholders.

A row is only written when it is safe:
  - the row's current text equals `prod_text` (otherwise it changed since the CSV
    was built and is reported as drifted, not overwritten), and
  - the new text keeps exactly the English source's placeholders.

Runs as a dry run unless --apply is given.

Usage:
    python manage.py apply_translation_fixes fixes.csv
    cat fixes.csv | python manage.py apply_translation_fixes -
    python manage.py apply_translation_fixes fixes.csv --skip progressBar.stepOf:my
    python manage.py apply_translation_fixes fixes.csv --apply
"""

import argparse
import csv
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from translations.models import Translation
from translations.placeholders import extract_placeholders


class Command(BaseCommand):
    help = "Overwrite translations from a CSV when safe (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument(
            "data",
            nargs="?",
            type=argparse.FileType("r", encoding="utf-8"),
            default=sys.stdin,
            help="CSV with columns label, lang, prod_text, staging_text. Defaults to stdin.",
        )
        parser.add_argument(
            "--skip",
            action="append",
            default=[],
            metavar="LABEL:LANG",
            help="Leave this row alone (repeatable), e.g. progressBar.stepOf:my",
        )
        parser.add_argument("--apply", action="store_true", help="Write the changes. Without it nothing is changed.")

    def handle(self, *args, **options):
        source = settings.LANGUAGE_CODE
        skip = set(options["skip"])
        reader = csv.DictReader(options["data"])
        missing_cols = {"label", "lang", "prod_text", "staging_text"} - set(reader.fieldnames or [])
        if missing_cols:
            raise CommandError(f"CSV is missing columns: {sorted(missing_cols)}")

        planned, skipped, drifted, unsafe, absent = [], [], [], [], []
        for row in reader:
            label, lang = row["label"], row["lang"]
            if f"{label}:{lang}" in skip:
                skipped.append((label, lang))
                continue
            parent = Translation.objects.prefetch_related("translations").filter(label=label, active=True).first()
            current = {t.language_code: t for t in parent.translations.all()} if parent else {}
            if lang not in current or source not in current:
                absent.append((label, lang))
                continue
            if current[lang].text != row["prod_text"]:
                drifted.append((label, lang))
                continue
            if extract_placeholders(row["staging_text"]) != extract_placeholders(current[source].text):
                unsafe.append((label, lang))
                continue
            planned.append((parent.pk, label, lang, row["prod_text"], row["staging_text"], current[lang].edited))

        verb = "Updated" if options["apply"] else "Would update"
        for pk, label, lang, before, after, edited in planned:
            self.stdout.write(f"{label} [{lang}]{' (edited)' if edited else ''}\n  - {before}\n  + {after}")
            if options["apply"]:
                # manual=edited keeps the row's existing edited flag; a non-manual write is only
                # refused when the row is already edited and no_auto, so pass the flag through.
                Translation.objects.edit_translation_by_id(pk, lang, after, manual=bool(edited))

        self.stdout.write(f"\n{verb}: {len(planned)}")
        for name, rows in (
            ("Skipped by --skip", skipped),
            ("Drifted since the CSV was built (not touched)", drifted),
            ("New text would break placeholders (not touched)", unsafe),
            ("Row or label not found (not touched)", absent),
        ):
            self.stdout.write(f"{name}: {len(rows)}")
            for label, lang in rows:
                self.stdout.write(f"  {label} [{lang}]")
        if not options["apply"] and planned:
            self.stdout.write("\nDry run. Re-run with --apply to write these changes.")
