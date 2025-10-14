from typing import Any
from django.db import models
from simple_history.models import HistoricalRecords
from parler.models import TranslatableModel, TranslatedFields, TranslatableManager
from django.conf import settings
from dataclasses import dataclass
from integrations.util.cache import Cache
from translations.model_data import ModelDataController
from sentry_sdk import capture_exception

BLANK_TRANSLATION_PLACEHOLDER = "[PLACEHOLDER]"


class TranslationCache(Cache):
    expire_time = 24 * 60 * 60
    default = {}

    def update(self):
        langs = [lang["code"] for lang in settings.PARLER_LANGUAGES[None]]
        translations = Translation.objects.prefetch_related("translations")
        translations_dict = {}
        for lang in langs:
            lang_translations = {}
            for translation in translations:
                if translation.active:
                    translation.set_current_language(lang)
                    lang_translations[translation.label] = translation.text
            translations_dict[lang] = lang_translations
        return translations_dict


class TranslationManager(TranslatableManager):
    use_in_migrations = True
    translation_cache = TranslationCache()
    all_langs = [lang["code"] for lang in settings.PARLER_LANGUAGES[None]]

    def add_translation(self, label, default_message=BLANK_TRANSLATION_PLACEHOLDER, active=True, no_auto=False):
        default_lang = settings.LANGUAGE_CODE
        parent = self.get_or_create(label=label, defaults={"active": active, "no_auto": no_auto})[0]
        if parent.active != active or parent.no_auto != no_auto:
            parent.active = active
            parent.no_auto = no_auto
            parent.save()

        parent.create_translation(default_lang, text=default_message, edited=True)

        for lang in self.all_langs:
            if lang == default_lang:
                continue

            parent.create_translation(lang, text="", edited=False)
        self.translation_cache.invalid = True
        return parent

    def edit_translation(self, label, lang, translation, manual=True):
        parent = self.language(lang).get(label=label)

        if manual is False and parent.no_auto and parent.edited:
            return parent

        parent.text = translation
        parent.edited = manual
        parent.save()
        self.translation_cache.invalid = True
        return parent

    def edit_translation_by_id(self, id, lang, translation, manual=True):
        parent = self.prefetch_related("translations").language(lang).get(pk=id)

        if manual is False and parent.no_auto and parent.edited:
            return parent

        parent.text = translation
        parent.edited = manual
        parent.save()
        self.translation_cache.invalid = True
        return parent

    def all_translations(self, langs=all_langs):
        translations_dict = {}
        for lang in langs:
            translations_dict[lang] = self.translation_cache.fetch()[lang]

        return translations_dict

    def export_translations(self):
        all_langs = settings.PARLER_LANGUAGES[None]
        translations = self.prefetch_related("translations")

        translations_export = {"translations": {}, "model_data": {}}
        for translation in translations:
            related_instances = translation.get_reverse_instances()

            for relationship in related_instances:
                instance = relationship.instance

                if instance.external_name is None:
                    continue

                field_name = relationship.field_name
                TranslationExportBuilder: type[ModelDataController] = getattr(
                    instance, "TranslationExportBuilder", ModelDataController
                )

                export_builder = TranslationExportBuilder(instance)

                model_data = translations_export["model_data"]
                model_name = export_builder.model_name
                if model_name not in model_data:
                    model_data[model_name] = {
                        "meta_data": {"dependencies": TranslationExportBuilder.dependencies, "name": model_name},
                        "instance_data": {},
                    }
                instance_data = model_data[model_name]["instance_data"]

                if export_builder.external_name not in instance_data:
                    instance_data[export_builder.external_name] = {
                        "data": export_builder.to_model_data(),
                        "labels": {},
                        "external_name": export_builder.external_name,
                    }

                instance_data[export_builder.external_name]["labels"][field_name] = translation.label

            translations_export["translations"][translation.label] = {
                "langs": {},
                "no_auto": translation.no_auto,
                "active": translation.active,
            }

            for lang in all_langs:
                translation.set_current_language(lang["code"])
                translations_export["translations"][translation.label]["langs"][lang["code"]] = (
                    translation.text,
                    translation.edited,
                )

        return translations_export


class CustomHistoricalRecords(HistoricalRecords):

    def get_history_model_name(self, model):
        return f"Historical{model._meta.object_name}"

    def create_history_model(self, model, inherited):
        history_model = super().create_history_model(model, inherited)

        history_model.add_to_class("affected_language", models.CharField(max_length=16, null=True, blank=True))
        history_model.add_to_class("original_text", models.TextField(null=True, blank=True))
        history_model.add_to_class("changed_text", models.TextField(null=True, blank=True))
        history_model.add_to_class("edit_type", models.BooleanField(null=True, blank=True))

        return history_model


class Translation(TranslatableModel):
    history = CustomHistoricalRecords()
    translations = TranslatedFields(
        text=models.TextField(null=True, blank=True), edited=models.BooleanField(default=False, null=False)
    )
    active = models.BooleanField(default=True, null=False)
    no_auto = models.BooleanField(default=False, null=False)
    label = models.CharField(max_length=128, null=False, blank=False, unique=True)

    objects = TranslationManager()

    def save(self, *args, **kwargs):
        """
        This overrides the save method to track translation changes
        and save them in the history model.
        """
        is_new = self.pk is None

        old_translations = {}
        if not is_new:
            try:
                old_instance = Translation.objects.get(pk=self.pk)
                for lang_code, _ in settings.LANGUAGES:
                    if old_instance.has_translation(lang_code):
                        old_text = old_instance.safe_translation_getter(
                            "text",
                            language_code=lang_code,
                            any_language=False,
                        )
                        old_edited = old_instance.safe_translation_getter(
                            "edited",
                            language_code=lang_code,
                            any_language=False,
                        )
                        old_translations[lang_code] = {
                            "text": old_text,
                            "edited": old_edited,
                        }
                    else:
                        old_translations[lang_code] = None
            except Translation.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        for lang_code, _ in settings.LANGUAGES:
            try:
                self.set_current_language(lang_code)
                new_text = self.text
                new_edited = self.edited

                old = old_translations.get(lang_code)
                if old is None:
                    continue

                if old["text"] != new_text:
                    latest_history = self.history.first()
                    if latest_history:
                        latest_history.affected_language = lang_code
                        latest_history.original_text = old["text"]
                        latest_history.changed_text = new_text
                        latest_history.edit_type = new_edited
                        latest_history.save()
            except Exception as e:
                capture_exception(e, level="warning", extras={"lang_code": lang_code, "translation_id": self.pk})

    def _get_reverses(self):
        """
        This method checks if the current Translation object is referenced by any related models
        such as Program, Navigator, UrgentNeed, or Document. It iterates through all reverse
        relationships of the Translation model and determines if any related object exists.
        It returns all of teh reverse relationships
        """

        relationships = []

        # determine if a translation is refrenced by either a program, navigator, urgent_need, or document
        # https://stackoverflow.com/questions/54711671/django-how-to-determine-if-an-object-is-referenced-by-any-other-object
        for reverse in (f for f in self._meta.get_fields() if f.auto_created and not f.concrete):
            if reverse.related_name == "translations":
                continue

            name = reverse.get_accessor_name()

            reverse_count = getattr(self, name).count()
            if reverse_count > 0:
                relationships.append(reverse)

        return relationships

    @dataclass
    class ReverseInstance:
        instance: Any
        field_name: Any

    def get_reverse_instances(self) -> list[ReverseInstance]:
        """
        Get list of instances and their relationship name that refrence this translation
        """
        reverses = self._get_reverses()

        instances: list[self.ReverseInstance] = []
        for reverse in reverses:
            name = reverse.get_accessor_name()
            instances.extend([self.ReverseInstance(instance, name) for instance in getattr(self, name).all()])

        return instances

    @property
    def used_by(self):
        """
        This property field stores information about the first model instance that uses
        this Translation object. It checks for related models and, if a relationship
        is found, retrieves the instance's ID, model name, field name, and display name (either
        an external name or an abbreviated name). If no relationship is found, it returns
        default values indicating the translation is unassigned.
        """
        reverses = self._get_reverses()
        if len(reverses) >= 1:
            reverse = reverses[0]
            instance = getattr(self, reverse.get_accessor_name()).first()
            model_name = reverse.related_model._meta.model_name
            field_name = reverse.field.name
            external_name = getattr(instance, "external_name", None)
            abbreviated_name = getattr(instance, "abbreviated_name", None)
            display_name = external_name if external_name else abbreviated_name
            return {"id": instance.id, "model_name": model_name, "field_name": field_name, "display_name": display_name}
        return {"id": None, "model_name": "unassigned", "field_name": None, "display_name": None}

    def get_lang(self, lang):
        return self.translations.filter(language_code=lang).first()

    @property
    def default_message(self):
        return self.get_lang(settings.LANGUAGE_CODE).text

    def __str__(self):
        return self.label
