import json

import pytest
from django.core.management import call_command

from integrations.clients.google_translate import Translate
from programs.models import UrgentNeed, UrgentNeedType
from screener.models import WhiteLabel


@pytest.fixture(autouse=True)
def stub_translate(monkeypatch):
    """Avoid real Google Translate calls during tests."""

    monkeypatch.setattr(Translate, "__init__", lambda self: None)

    def fake_bulk_translate(self, langs, texts):
        targets = Translate.languages if "__all__" in langs else langs
        return {text: {lang: text for lang in targets} for text in texts}

    monkeypatch.setattr(Translate, "bulk_translate", fake_bulk_translate)


@pytest.mark.django_db
def test_import_urgent_need_creates_entities(tmp_path):
    white_label = WhiteLabel.objects.create(name="Test", code="test", state_code="TS")

    config = {
        "white_label": {"code": "test"},
        "need": {
            "external_name": "tx_diaper_bank",
            "category_type": {
                "external_name": "diapers_and_baby_supplies",
                "name": "Diapers and baby supplies",
                "icon": "diapers_and_baby_supplies",
            },
            "type_short": ["baby supplies"],
            "functions": [],
            "phone_number": "+13035550000",
            "counties": [
                "Travis",
                "Dallas",
                "El Paso",
                "Tarrant",
                "Galveston",
                "Brazoria",
                "Collin",
                "Bexar",
                "McLennan",
            ],
            "required_expense_types": ["childSupport"],
            "fpl": {"year": "2024", "period": "2024"},
            "translations": {
                "name": "National Diaper Bank Network",
                "description": "Use to find access to baby diapers, wipes, and other new baby needs.",
                "link": "https://nationaldiaperbanknetwork.org/member-directory/",
                "warning": "",
                "website_description": "Map to find local diaper banks in your area.",
                "notification_message": "",
            },
        },
    }

    config_path = tmp_path / "need.json"
    config_path.write_text(json.dumps(config))

    call_command("import_urgent_need_config", str(config_path))

    need = UrgentNeed.objects.get(external_name="tx_diaper_bank")

    assert need.white_label == white_label
    assert str(need.phone_number) == "+13035550000"

    assert need.category_type is not None
    assert need.category_type.external_name == "diapers_and_baby_supplies"
    assert need.category_type.icon is not None
    assert need.category_type.icon.name == "diapers_and_baby_supplies"

    assert set(need.type_short.values_list("name", flat=True)) == {"baby supplies"}
    assert set(need.county_names) == {
        "Travis",
        "Dallas",
        "El Paso",
        "Tarrant",
        "Galveston",
        "Brazoria",
        "Collin",
        "Bexar",
        "McLennan",
    }
    assert need.required_expense_type_names == ["childSupport"]

    assert need.year is not None
    assert need.year.year == "2024"

    assert need.name.safe_translation_getter("text", any_language=False) == "National Diaper Bank Network"
    assert (
        need.description.safe_translation_getter("text", any_language=False)
        == "Use to find access to baby diapers, wipes, and other new baby needs."
    )
    assert (
        need.link.safe_translation_getter("text", any_language=False)
        == "https://nationaldiaperbanknetwork.org/member-directory/"
    )
    assert (
        need.website_description.safe_translation_getter("text", any_language=False)
        == "Map to find local diaper banks in your area."
    )
    assert need.notification_message.safe_translation_getter("text", any_language=False) == ""

    # Category type translation set
    category_type = UrgentNeedType.objects.get(external_name="diapers_and_baby_supplies")
    assert category_type.name.safe_translation_getter("text", any_language=False) == "Diapers and baby supplies"


@pytest.mark.django_db
def test_import_urgent_need_dry_run(tmp_path):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")

    config = {
        "white_label": {"code": "test"},
        "need": {
            "external_name": "dry_run_need",
            "category_type": {"external_name": "diapers_and_baby_supplies", "name": "Diapers and baby supplies"},
            "type_short": ["baby supplies"],
            "translations": {
                "name": "Dry Run need",
                "description": "Description",
                "link": "https://example.com",
                "warning": "Warning",
                "website_description": "Website description",
            },
        },
    }

    config_path = tmp_path / "need_dry.json"
    config_path.write_text(json.dumps(config))

    call_command("import_urgent_need_config", str(config_path), "--dry-run")

    assert UrgentNeed.objects.filter(external_name="dry_run_need").count() == 0
