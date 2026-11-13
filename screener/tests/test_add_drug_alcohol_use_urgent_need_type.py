"""
Tests for the MFB-2363 migrations that add the "Help with drug or alcohol use"
urgent need type and category.

pytest runs with --nomigrations, so the migration functions are called directly
against rows built here.
"""

import importlib
from unittest.mock import patch

from django.apps import apps as django_apps
from django.conf import settings
from django.test import TestCase

from programs.models import UrgentNeed, UrgentNeedCategory, UrgentNeedType
from screener.models import WhiteLabel
from screener.urgent_needs import NEED_CATEGORY_FIELDS

type_migration = importlib.import_module("programs.migrations.0209_add_drug_alcohol_use_urgent_need_type")
category_migration = importlib.import_module("programs.migrations.0210_add_drug_alcohol_use_category")

ADC_EXTERNAL_NAME = category_migration.ALCOHOL_DRUG_COUNCIL_EXTERNAL_NAME


class TestAddDrugAlcoholUseUrgentNeedType(TestCase):
    def setUp(self) -> None:
        # The migration machine-translates the name; keep tests off the network.
        translate = patch.object(type_migration, "Translate")
        self.translate = translate.start()
        self.translate.return_value.bulk_translate.return_value = {}
        self.addCleanup(translate.stop)

    def test_creates_a_shared_type_with_icon_and_english_name(self) -> None:
        type_migration.forward(None, None)

        urgent_need_type = UrgentNeedType.objects.get(external_name="drug_alcohol_use")
        self.assertIsNone(urgent_need_type.white_label)
        self.assertEqual(urgent_need_type.icon_name, "drug_alcohol_use")
        self.assertEqual(urgent_need_type.name.get_lang(settings.LANGUAGE_CODE).text, "Help with drug or alcohol use")

    def test_stores_machine_translations(self) -> None:
        self.translate.return_value.bulk_translate.return_value = {
            "Help with drug or alcohol use": {"es": "Ayuda con el uso de drogas o alcohol"}
        }

        type_migration.forward(None, None)

        urgent_need_type = UrgentNeedType.objects.get(external_name="drug_alcohol_use")
        self.assertEqual(urgent_need_type.name.get_lang("es").text, "Ayuda con el uso de drogas o alcohol")

    def test_a_translation_outage_does_not_fail_the_migration(self) -> None:
        self.translate.return_value.bulk_translate.side_effect = RuntimeError("translate is down")

        type_migration.forward(None, None)

        self.assertTrue(UrgentNeedType.objects.filter(external_name="drug_alcohol_use").exists())

    def test_running_twice_does_not_duplicate(self) -> None:
        type_migration.forward(None, None)
        type_migration.forward(None, None)

        self.assertEqual(UrgentNeedType.objects.filter(external_name="drug_alcohol_use").count(), 1)

    def test_backward_removes_the_type(self) -> None:
        type_migration.forward(None, None)

        type_migration.backward(None, None)

        self.assertFalse(UrgentNeedType.objects.filter(external_name="drug_alcohol_use").exists())


class TestAddDrugAlcoholUseCategory(TestCase):
    def setUp(self) -> None:
        translate = patch.object(type_migration, "Translate")
        translate.start().return_value.bulk_translate.return_value = {}
        self.addCleanup(translate.stop)

        self.nc = WhiteLabel.objects.create(name="North Carolina", code="nc", state_code="NC")
        type_migration.forward(None, None)
        self.new_type = UrgentNeedType.objects.get(external_name="drug_alcohol_use")

    def make_alcohol_drug_council(self) -> UrgentNeed:
        behavioral_health = UrgentNeedType.objects.new_urgent_need_type(None, "behavioral_health", None)
        mental_health, _ = UrgentNeedCategory.objects.get_or_create(name="mental health")

        need = UrgentNeed.objects.new_urgent_need(white_label="nc", name=ADC_EXTERNAL_NAME, phone_number=None)
        need.category_type = behavioral_health
        need.save()
        need.type_short.set([mental_health])
        return need

    def test_seeds_a_category_the_screener_recognizes(self) -> None:
        category_migration.add_urgent_need_categories(django_apps, None)

        self.assertTrue(UrgentNeedCategory.objects.filter(name="drug alcohol use").exists())
        self.assertIn("drug alcohol use", NEED_CATEGORY_FIELDS)

    def test_swaps_alcohol_drug_council_onto_the_new_type_and_category(self) -> None:
        need = self.make_alcohol_drug_council()

        category_migration.add_urgent_need_categories(django_apps, None)

        need.refresh_from_db()
        self.assertEqual(need.category_type_id, self.new_type.id)
        self.assertEqual(list(need.type_short.values_list("name", flat=True)), ["drug alcohol use"])

    def test_missing_resource_is_skipped(self) -> None:
        category_migration.add_urgent_need_categories(django_apps, None)

        self.assertFalse(UrgentNeed.objects.filter(external_name=ADC_EXTERNAL_NAME).exists())
