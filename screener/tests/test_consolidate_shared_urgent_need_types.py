"""
Tests for the migration that consolidates UrgentNeedType onto shared rows.

pytest runs with --nomigrations, so forward() is called directly against rows
built here.
"""

import importlib
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from programs.models import UrgentNeed, UrgentNeedType
from screener.models import WhiteLabel
from translations.models import Translation

migration = importlib.import_module("programs.migrations.0188_consolidate_shared_urgent_need_types")


def make_type(external_name: str, white_label: str, name: str) -> UrgentNeedType:
    urgent_need_type = UrgentNeedType.objects.new_urgent_need_type(white_label, external_name, None)
    Translation.objects.edit_translation_by_id(urgent_need_type.name.id, settings.LANGUAGE_CODE, name)
    return urgent_need_type


def make_need(external_name: str, white_label: WhiteLabel, category_type: UrgentNeedType) -> UrgentNeed:
    need = UrgentNeed.objects.new_urgent_need(white_label=white_label.code, name=external_name, phone_number=None)
    need.category_type = category_type
    need.save()
    return need


def english_name(urgent_need_type: UrgentNeedType) -> str:
    return urgent_need_type.name.get_lang(settings.LANGUAGE_CODE).text


class TestConsolidateSharedUrgentNeedTypes(TestCase):
    def setUp(self) -> None:
        # The migration machine-translates renamed types; keep tests off the network.
        translate = patch.object(migration, "Translate")
        translate.start().return_value.bulk_translate.return_value = {}
        self.addCleanup(translate.stop)

        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.ks = WhiteLabel.objects.create(name="Kansas", code="ks", state_code="KS")

    def test_the_row_with_the_canonical_name_is_promoted_and_the_rest_merge_into_it(self) -> None:
        """
        CO holds the external_name baby_supplies, but KS holds the canonical
        wording. The KS row must survive under CO's name, carrying CO's needs.
        """
        co_row = make_type("baby_supplies", "co", "Baby supplies")
        ks_row = make_type("ks_baby_supplies", "ks", "Diapers and other baby supplies")
        co_need = make_need("co_diaper_bank", self.co, co_row)
        ks_need = make_need("ks_diaper_bank", self.ks, ks_row)

        migration.forward(None, None)

        shared = UrgentNeedType.objects.get(external_name="baby_supplies")
        self.assertEqual(shared.id, ks_row.id)
        self.assertIsNone(shared.white_label)
        self.assertEqual(english_name(shared), "Diapers and other baby supplies")
        self.assertEqual(shared.icon_name, "baby_supplies")
        self.assertFalse(UrgentNeedType.objects.filter(id=co_row.id).exists())

        co_need.refresh_from_db()
        ks_need.refresh_from_db()
        self.assertEqual(co_need.category_type_id, shared.id)
        self.assertEqual(ks_need.category_type_id, shared.id)

    def test_a_drifted_name_is_replaced_with_the_canonical_one(self) -> None:
        make_type("tx_managing_housing_cost", "co", "Managing Housing Cost")

        migration.forward(None, None)

        self.assertEqual(
            english_name(UrgentNeedType.objects.get(external_name="managing_housing_costs")), "Managing housing costs"
        )

    def test_an_unmapped_white_label_row_fails_the_migration(self) -> None:
        make_type("ks_something_new", "ks", "Something new")

        with self.assertRaisesMessage(RuntimeError, "ks:ks_something_new"):
            migration.forward(None, None)

    def test_an_empty_database_gets_every_shared_type(self) -> None:
        migration.forward(None, None)

        self.assertEqual(
            set(UrgentNeedType.objects.values_list("external_name", flat=True)), set(migration.SHARED_TYPES)
        )
        self.assertFalse(UrgentNeedType.objects.filter(white_label__isnull=False).exists())


def test_every_urgent_need_config_names_a_shared_type() -> None:
    """
    The importer never edits an existing type, so a config carrying an old
    per-white-label name would fail, and a stray name or icon would be rejected.
    """
    data_dir = Path(__file__).resolve().parents[2] / "programs/management/commands/import_urgent_need_config_data/data"
    configs = sorted(data_dir.glob("*.json"))
    assert configs

    for path in configs:
        category_type = json.loads(path.read_text(encoding="utf-8"))["need"]["category_type"]
        assert category_type == {"external_name": category_type["external_name"]}, path.name
        assert category_type["external_name"] in migration.SHARED_TYPES, path.name
