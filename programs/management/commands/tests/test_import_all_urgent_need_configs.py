import json
from pathlib import Path

import pytest
from django.core.management import call_command

from integrations.clients.google_translate import Translate
from programs.management.commands import import_all_urgent_need_configs
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


@pytest.fixture
def data_dir(tmp_path, monkeypatch) -> Path:
    """Point the command at a temporary data directory."""

    directory = tmp_path / "data"
    directory.mkdir()
    monkeypatch.setattr(import_all_urgent_need_configs.Command, "DATA_DIR", directory)
    return directory


def write_config(data_dir: Path, external_name: str, white_label: str = "test", **overrides) -> Path:
    need = {
        "external_name": external_name,
        "category_type": {"external_name": f"ct_{external_name}", "name": "Category"},
        "type_short": ["food"],
        "translations": {
            "name": f"Name {external_name}",
            "description": "Desc",
            "link": "https://example.com",
            "warning": "",
            "website_description": "Site",
        },
    }
    need.update(overrides)

    path = data_dir / f"{external_name}.json"
    path.write_text(json.dumps({"white_label": {"code": white_label}, "need": need}))
    return path


@pytest.mark.django_db
def test_imports_every_pending_config(data_dir):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")
    write_config(data_dir, "need_one")
    write_config(data_dir, "need_two")

    call_command("import_all_urgent_need_configs")

    assert set(UrgentNeed.objects.values_list("external_name", flat=True)) == {"need_one", "need_two"}


@pytest.mark.django_db
def test_skips_configs_that_already_exist(data_dir):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")
    write_config(data_dir, "need_one")

    call_command("import_all_urgent_need_configs")
    original_id = UrgentNeed.objects.get(external_name="need_one").id

    call_command("import_all_urgent_need_configs")

    assert UrgentNeed.objects.get(external_name="need_one").id == original_id


@pytest.mark.django_db
def test_dry_run_makes_no_changes(data_dir):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")
    write_config(data_dir, "need_one")

    call_command("import_all_urgent_need_configs", "--dry-run")

    assert not UrgentNeed.objects.exists()


@pytest.mark.django_db
def test_white_label_filter_only_imports_matching_configs(data_dir):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")
    WhiteLabel.objects.create(name="Other", code="other", state_code="OT")
    write_config(data_dir, "need_one", white_label="test")
    write_config(data_dir, "need_two", white_label="other")

    call_command("import_all_urgent_need_configs", "--white-label", "other")

    assert set(UrgentNeed.objects.values_list("external_name", flat=True)) == {"need_two"}


@pytest.mark.django_db
def test_unscoped_override_is_refused(data_dir):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")
    write_config(data_dir, "need_one")

    call_command("import_all_urgent_need_configs")
    original_id = UrgentNeed.objects.get(external_name="need_one").id

    # A bare --override would recreate every urgent need in the database, discarding admin edits.
    call_command("import_all_urgent_need_configs", "--override")

    assert UrgentNeed.objects.get(external_name="need_one").id == original_id


@pytest.mark.django_db
def test_scoped_override_recreates_the_need(data_dir):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")
    write_config(data_dir, "need_one")
    write_config(data_dir, "need_two")

    call_command("import_all_urgent_need_configs")
    one_id = UrgentNeed.objects.get(external_name="need_one").id
    two_id = UrgentNeed.objects.get(external_name="need_two").id

    call_command("import_all_urgent_need_configs", "--override", "--file", "need_one.json")

    assert UrgentNeed.objects.get(external_name="need_one").id != one_id
    assert UrgentNeed.objects.get(external_name="need_two").id == two_id


@pytest.mark.django_db
def test_unreadable_config_does_not_stop_the_run(data_dir):
    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")
    (data_dir / "broken.json").write_text("{ invalid json")
    write_config(data_dir, "need_one")

    call_command("import_all_urgent_need_configs")

    assert set(UrgentNeed.objects.values_list("external_name", flat=True)) == {"need_one"}


@pytest.mark.django_db
def test_reused_category_type_keeps_its_name_when_config_omits_it(data_dir):
    """Configs that point at a shared UrgentNeedType must not relabel it."""

    WhiteLabel.objects.create(name="Test", code="test", state_code="TS")
    write_config(data_dir, "need_one", category_type={"external_name": "shared_ct", "name": "Original"})
    call_command("import_all_urgent_need_configs")

    write_config(data_dir, "need_two", category_type={"external_name": "shared_ct"})
    call_command("import_all_urgent_need_configs")

    category_type = UrgentNeedType.objects.get(external_name="shared_ct")
    assert category_type.name.safe_translation_getter("text", any_language=False) == "Original"
