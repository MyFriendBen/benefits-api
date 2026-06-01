import argparse
import json
from sys import stdin

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from integrations.clients.google_translate import Translate
from translations.models import Translation


class Command(BaseCommand):
    help = """
    Add translation labels from a flat {label: english_text} JSON map, then
    auto-translate each new/changed string into every supported language.

    Intended for the common "a feature PR introduces N new copy strings" case:
    extract the FormattedMessage / intl.formatMessage IDs and their English
    defaults from the PR's code into a JSON map, then feed it here.

    Input is a JSON object of {label: english_text}, e.g.
        {
          "energyCalculator.calculateImpact.titleLabel": "Bill Impact Calculator",
          "energyCalculator.calculateImpact.submit": "Calculate impact"
        }
    read from a file argument or stdin.

    Examples:
        python manage.py add_translations strings.json
        cat strings.json | python manage.py add_translations
        python manage.py add_translations strings.json --dry-run
        python manage.py add_translations strings.json --no-translate

    Idempotent: re-running updates English text and backfills missing languages.
    Use --dry-run first to preview exactly what would change without writing
    anything or calling the translation API.

    For importing a *pre-translated* full export (per-language text plus the
    no_auto/active/edited flags), use `bulk_add_translations` instead — that
    command takes the export shape and does not auto-translate.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "data",
            nargs="?",
            type=argparse.FileType("r", encoding="utf-8"),
            default=stdin,
            help="JSON file mapping {label: english_text}. Defaults to stdin.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change and exit without writing or calling the translation API.",
        )
        parser.add_argument(
            "--no-translate",
            action="store_true",
            help="Only add/update the English rows; do not auto-translate to other languages.",
        )
        parser.add_argument(
            "--no-auto",
            action="store_true",
            help="Set no_auto=True on the labels (protects manually-edited translations from being overwritten).",
        )
        parser.add_argument(
            "--inactive",
            action="store_true",
            help="Create the labels as inactive (active=False).",
        )

    def _load_data(self, options):
        try:
            data = json.load(options["data"])
        except json.JSONDecodeError as e:
            raise CommandError(f"Input is not valid JSON: {e}")

        if not isinstance(data, dict):
            raise CommandError("Input JSON must be an object mapping {label: english_text}.")

        cleaned = {}
        for label, text in data.items():
            if not isinstance(label, str) or not label.strip():
                raise CommandError(f"Invalid label (must be a non-empty string): {label!r}")
            if not isinstance(text, str):
                raise CommandError(f"Value for {label!r} must be a string, got {type(text).__name__}.")
            cleaned[label] = text
        return cleaned

    def _classify(self, label, english_text):
        """Return ('new'|'update'|'unchanged', existing_english_or_None) for reporting."""
        existing = Translation.objects.filter(label=label).first()
        if existing is None:
            return "new", None

        existing.set_current_language(settings.LANGUAGE_CODE)
        current = existing.text if existing.has_translation(settings.LANGUAGE_CODE) else None
        if current == english_text:
            return "unchanged", current
        return "update", current

    def handle(self, *args, **options):
        data = self._load_data(options)
        dry_run = options["dry_run"]
        no_translate = options["no_translate"]
        active = not options["inactive"]
        no_auto = options["no_auto"]

        if not data:
            self.stdout.write(self.style.WARNING("No labels in input; nothing to do."))
            return

        target_languages = [
            lang["code"] for lang in settings.PARLER_LANGUAGES[None] if lang["code"] != settings.LANGUAGE_CODE
        ]

        # ---- Classify everything up front (read-only) so dry-run and real run agree. ----
        new_labels, update_labels, unchanged_labels = [], [], []
        for label, text in data.items():
            kind, current = self._classify(label, text)
            if kind == "new":
                new_labels.append(label)
            elif kind == "update":
                update_labels.append((label, current))
            else:
                unchanged_labels.append(label)

        self.stdout.write(
            f"{len(data)} label(s): "
            f"{len(new_labels)} new, {len(update_labels)} English-text change(s), "
            f"{len(unchanged_labels)} unchanged."
        )
        for label in new_labels:
            self.stdout.write(self.style.SUCCESS(f"  + {label}"))
        for label, current in update_labels:
            self.stdout.write(self.style.WARNING(f"  ~ {label}  (was: {current!r})"))

        if no_translate:
            self.stdout.write(
                f"Auto-translate: disabled (--no-translate). Target languages would be: {target_languages}"
            )
        else:
            self.stdout.write(f"Auto-translate target languages: {target_languages}")

        if dry_run:
            self.stdout.write(self.style.NOTICE("\nDry run — no changes written, no translation API calls made."))
            return

        # ---- Add / update English rows. ----
        self.stdout.write("\nWriting English translations...")
        translation_objects = []
        for label, text in data.items():
            translation_obj = Translation.objects.add_translation(
                label=label, default_message=text, active=active, no_auto=no_auto
            )
            translation_objects.append((translation_obj, text))

        if no_translate:
            self.stdout.write(
                self.style.SUCCESS(f"Added/updated {len(data)} English label(s). Skipped auto-translate.")
            )
            return

        # ---- Auto-translate, batched: dedup identical English strings, one bulk call per unique text. ----
        self.stdout.write("Auto-translating to other languages...")
        translate = Translate()

        # Map unique English text -> list of translation objects that share it.
        by_text: dict[str, list] = {}
        for translation_obj, text in translation_objects:
            if text and text.strip():
                by_text.setdefault(text, []).append(translation_obj)

        unique_texts = list(by_text.keys())
        if not unique_texts:
            self.stdout.write(self.style.SUCCESS("No non-empty English text to translate."))
            return

        try:
            # "__all__" expands to every configured non-default language inside the client.
            results = translate.bulk_translate(["__all__"], unique_texts)
        except Exception as e:
            raise CommandError(f"Translation API call failed; English rows were saved. Re-run to retry. Error: {e}")

        translated_records = 0
        for text, lang_map in results.items():
            for translation_obj in by_text[text]:
                for lang, translated_text in lang_map.items():
                    Translation.objects.edit_translation_by_id(translation_obj.id, lang, translated_text, manual=False)
                    translated_records += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Added/updated {len(data)} label(s); wrote {translated_records} "
                f"translated record(s) across {len(target_languages)} language(s)."
            )
        )
