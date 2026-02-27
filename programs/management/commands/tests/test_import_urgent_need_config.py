import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

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


@pytest.mark.django_db
def test_import_urgent_need_override_recreates(tmp_path):
    white_label = WhiteLabel.objects.create(name="Test", code="test", state_code="TS")

    base_config = {
        "white_label": {"code": "test"},
        "need": {
            "external_name": "override_need",
            "category_type": {"external_name": "ct_one"},
            "type_short": ["one"],
            "translations": {
                "name": "Need One",
                "description": "Desc one",
                "link": "https://example.com/one",
                "warning": "",
                "website_description": "Site one",
            },
        },
    }

    config_path = tmp_path / "need_override.json"
    config_path.write_text(json.dumps(base_config))
    call_command("import_urgent_need_config", str(config_path))

    original = UrgentNeed.objects.get(external_name="override_need")

    # Override with changed category and translation
    override_config = base_config.copy()
    override_config["need"] = {
        **base_config["need"],
        "category_type": {"external_name": "ct_two", "name": "Category Two"},
        "type_short": ["two"],
        "translations": {
            "name": "Need Two",
            "description": "Desc two",
            "link": "https://example.com/two",
            "warning": "",
            "website_description": "Site two",
        },
    }

    config_path.write_text(json.dumps(override_config))
    call_command("import_urgent_need_config", str(config_path), "--override")

    recreated = UrgentNeed.objects.get(external_name="override_need")

    assert UrgentNeed.objects.filter(external_name="override_need").count() == 1
    assert recreated.id != original.id  # type: ignore[attr-defined]
    assert recreated.category_type is not None
    assert recreated.category_type.external_name == "ct_two"
    assert set(recreated.type_short.values_list("name", flat=True)) == {"two"}
    assert recreated.name.safe_translation_getter("text", any_language=False) == "Need Two"


@pytest.mark.django_db
def test_import_fails_on_missing_white_label(tmp_path):
    config = {
        "white_label": {"code": "missing"},
        "need": {
            "external_name": "need",
            "category_type": {"external_name": "ct"},
            "type_short": ["one"],
            "translations": {
                "name": "Name",
                "description": "Desc",
                "link": "https://example.com",
                "warning": "",
                "website_description": "Site",
            },
        },
    }
    path = tmp_path / "missing_white_label.json"
    path.write_text(json.dumps(config))

    with pytest.raises(CommandError):
        call_command("import_urgent_need_config", str(path))


@pytest.mark.django_db
def test_import_fails_on_invalid_function(tmp_path):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")

    config = {
        "white_label": {"code": "test"},
        "need": {
            "external_name": "need",
            "category_type": {"external_name": "ct"},
            "type_short": ["one"],
            "functions": ["not_a_function"],
            "translations": {
                "name": "Name",
                "description": "Desc",
                "link": "https://example.com",
                "warning": "",
                "website_description": "Site",
            },
        },
    }

    path = tmp_path / "invalid_function.json"
    path.write_text(json.dumps(config))

    with pytest.raises(CommandError):
        call_command("import_urgent_need_config", str(path))


def test_import_fails_on_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{ invalid json")

    with pytest.raises(CommandError):
        call_command("import_urgent_need_config", str(path))


@pytest.mark.django_db
def test_import_fails_on_empty_type_short(tmp_path):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")

    config = {
        "white_label": {"code": "test"},
        "need": {
            "external_name": "need",
            "category_type": {"external_name": "ct"},
            "type_short": [],
            "translations": {
                "name": "Name",
                "description": "Desc",
                "link": "https://example.com",
                "warning": "",
                "website_description": "Site",
            },
        },
    }

    path = tmp_path / "empty_type_short.json"
    path.write_text(json.dumps(config))

    with pytest.raises(CommandError):
        call_command("import_urgent_need_config", str(path))
