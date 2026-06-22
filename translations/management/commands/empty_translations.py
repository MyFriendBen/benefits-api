from django.core.management.base import BaseCommand
from django.conf import settings
from parler.models import TranslationDoesNotExist
from translations.models import BLANK_TRANSLATION_PLACEHOLDER, Translation
from django.urls import reverse


class Command(BaseCommand):
    help = """
    Find empty translations
    """

    def add_arguments(self, parser) -> None:
        parser.add_argument("languages", nargs="*", type=str, help="The list of states to update the config for")

    def handle(self, *args, **options) -> None:
        default_lang = settings.LANGUAGE_CODE
        all_languages = [lang["code"] for lang in settings.PARLER_LANGUAGES[None] if lang["code"] != default_lang]

        languages = options["languages"]

        invalid_langs = []
        for i, lang in enumerate(languages):
            if lang not in all_languages:
                self.stdout.write(
                    f"'{lang}' in not a valid language. The options are: {', '.join(all_languages)}", self.style.WARNING
                )
                invalid_langs.append(i)

        # loop through in reverse so that the indexes don't shift
        for invalid_lang_index in invalid_langs[::-1]:
            del languages[invalid_lang_index]

        if len(languages) == 0:
            languages = all_languages

        for translation in Translation.objects.filter(active=True).prefetch_related("translations"):
            default_text = translation.text

            if default_text == "" or default_text == BLANK_TRANSLATION_PLACEHOLDER:
                continue

            for lang in languages:
                try:
                    translated_text = translation.translations.get(language_code=lang).text
                except TranslationDoesNotExist:
                    self._missing_translation_message(translation.id, lang)
                    continue

                if translated_text == "":
                    self._missing_translation_message(translation.id, lang)

        self.stdout.write("\nDONE", self.style.SUCCESS)

    def _missing_translation_message(self, id, lang: str) -> None:
        url = reverse("translation_admin_url", args=[id])
        self.stdout.write(f"{lang}: {settings.BACKEND_DOMAIN}{url}")
