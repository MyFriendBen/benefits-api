from typing import Any, Iterable

from django.conf import settings
from django.core.management.base import CommandError

from integrations.clients.google_translate import Translate
from translations.models import Translation


class TranslationImportMixin:
    """Shared translation import helpers for management commands."""

    def _bulk_update_entity_translations(
        self,
        entity: Any,
        translations: dict[str, str],
        entity_label: str,
        translated_fields: Iterable[str],
        *,
        warn_unknown: bool = False,
    ) -> None:
        """
        Update multiple translation fields with optional auto-translate.

        Args:
            entity: Model instance owning the Translation FKs.
            translations: field_name -> English text.
            entity_label: Used for logging/error messages.
            translated_fields: Iterable of valid translatable field names.
            warn_unknown: If True, unknown fields are logged as warnings; otherwise raise.
        """
        texts_to_translate: list[str] = []
        translation_objects: dict[str, list[Translation]] = {}

        for field_name, english_text in translations.items():
            if field_name not in translated_fields:
                if warn_unknown:
                    self.stdout.write(self.style.WARNING(f"  Warning: Unknown {entity_label} field '{field_name}'"))  # type: ignore[attr-defined]
                    continue
                raise CommandError(f"Field '{field_name}' is not translatable for {entity_label}")

            translation_obj: Translation = getattr(entity, field_name)

            # Update translation
            self._update_translation_all_languages(
                translation_obj, english_text, texts_to_translate, translation_objects
            )

        # Bulk translate
        if texts_to_translate:
            self.stdout.write(f"  Translating {len(texts_to_translate)} field(s) to all languages...")  # type: ignore[attr-defined]

            bulk_translations = Translate().bulk_translate(Translate.languages, texts_to_translate)

            for english_text, translation_obj_list in translation_objects.items():
                auto_translations = bulk_translations[english_text]
                for translation_obj in translation_obj_list:
                    for lang in Translate.languages:
                        if lang != settings.LANGUAGE_CODE:
                            Translation.objects.edit_translation_by_id(
                                translation_obj.id,  # type: ignore[attr-defined]
                                lang,
                                auto_translations[lang],
                                manual=False,
                            )

        entity.save()

    def _update_translation_all_languages(
        self,
        translation_obj: Translation,
        text: str,
        texts_to_translate: list[str],
        translation_objects: dict[str, list[Translation]],
    ) -> None:
        """Update a translation for all languages with auto-translate support."""
        # Update English translation (manual=True)
        Translation.objects.edit_translation_by_id(  # type: ignore[attr-defined]
            translation_obj.id,
            settings.LANGUAGE_CODE,
            text,
            manual=True,
        )

        # Handle no_auto fields (copy English to all languages)
        if translation_obj.no_auto:
            for lang in Translate.languages:
                Translation.objects.edit_translation_by_id(  # type: ignore[attr-defined]
                    translation_obj.id,
                    lang,
                    text,
                    manual=False,
                )
        else:
            if text:
                if text not in translation_objects:
                    texts_to_translate.append(text)
                    translation_objects[text] = []
                translation_objects[text].append(translation_obj)
