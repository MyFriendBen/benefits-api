from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q, OuterRef, Exists
from translations.models import Translation
from integrations.clients.google_translate import Translate


class Command(BaseCommand):
    help = """
    Use Google Translate to translate into a new language
    """

    def add_arguments(self, parser):
        parser.add_argument("--limit", default=1, type=int)
        parser.add_argument("--all", default=False, type=bool)
        parser.add_argument("--lang", default=settings.LANGUAGE_CODE, type=str)
        parser.add_argument(
            "--force-translations", action="store_true", help="Force processing even if no translations need updating"
        )

    def handle(self, *args, **options):
        limit = 10_000 if options["all"] else min(10_000, options["limit"])
        max_batch_size = 128
        char_limit = 5_000
        lang = options["lang"]

        translate = Translate()

        translations = Translation.objects.prefetch_related("translations").language(settings.LANGUAGE_CODE).all()

        print(f"Total translations: {len(translations)}")

        # Count how many need translation using a single query
        from django.db.models import Q, OuterRef, Exists

        # Check which translations don't have a record for this language
        lang_exists = Translation.objects.filter(pk=OuterRef("pk"), translations__language_code=lang)

        # Debug the filtering - check translations that have English text
        from django.db.models import Exists

        # Find translations that have English text
        has_en_text = Translation.objects.filter(
            translations__language_code=settings.LANGUAGE_CODE,
            translations__text__isnull=False,
            translations__text__gt="",
        )

        total_en = Translation.objects.language(settings.LANGUAGE_CODE).count()
        has_text_count = has_en_text.count()
        auto_allowed = has_en_text.filter(no_auto=False).count()
        no_target_lang = has_en_text.filter(no_auto=False).filter(~Exists(lang_exists)).count()

        need_translation_count = no_target_lang

        print(f"Total en-us translations: {total_en}")
        print(f"With English text: {has_text_count}")
        print(f"Auto translation allowed: {auto_allowed}")
        print(f"Missing {lang} record: {no_target_lang}")
        print(f"Translations needing {lang} translation: {need_translation_count}")

        # Exit early if no translations need processing (unless forced)
        if need_translation_count == 0 and not options.get("force_translations", False):
            print(f"No translations need {lang} translation. Use --force-translations to run anyway.")
            return

        total_count = 0
        temp_chars = 0
        temp_count = 0
        texts = {}
        batches = []
        for translation in translations:
            text = translation.text
            current_translation = translation.get_lang(lang)
            is_edited = current_translation is not None and current_translation.edited
            if is_edited or translation.text is None:
                continue

            if translation.no_auto:
                translation.set_current_language(lang)
                translation.text = text
                translation.save()
                continue

            if temp_chars + len(text) > char_limit or temp_count + 1 > max_batch_size:
                batches.append(texts.copy())
                texts = {}
                temp_chars = 0
                temp_count = 0

            temp_chars += len(text)
            temp_count += 1
            total_count += 1

            if text not in texts:
                texts[text] = []
            texts[text].append(translation)

            if total_count >= limit:
                batches.append(texts)
                break

        print(f"Processing {len(batches)} batches for language {lang}")

        records_created = 0

        for i, batch in enumerate(batches):

            try:
                auto = translate.bulk_translate([lang], list(batch.keys()))

                for [original_text, new_text] in auto.items():
                    for trans in batch[original_text]:
                        Translation.objects.edit_translation_by_id(trans.id, lang, new_text[lang], manual=False)
                        records_created += 1

            except Exception as e:
                print(f"ERROR in batch {i+1}: {str(e)}")
                raise

        print(f"Bulk translate completed successfully for {lang}")
        print(f"Total records created/updated: {records_created}")
