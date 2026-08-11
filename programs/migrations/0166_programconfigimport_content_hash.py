import hashlib
from pathlib import Path

from django.db import migrations, models

# Kept in sync with `config_content_hash` in
# programs/management/commands/import_all_program_configs.py.
# Duplicated deliberately: migrations must stay self-contained.
DATA_DIR = (
    Path(__file__).resolve().parent.parent
    / "management"
    / "commands"
    / "import_program_config_data"
    / "data"
)


def backfill_content_hashes(apps, schema_editor):
    """
    Stamp existing tracking rows with the current hash of their config file.

    An empty hash means "applied before hashing existed" and is treated as
    up to date, so this backfill is what makes future edits to those configs
    detectable. Rows whose file no longer exists keep an empty hash.
    """
    ProgramConfigImport = apps.get_model("programs", "ProgramConfigImport")

    updated = []
    for record in ProgramConfigImport.objects.all():
        config_file = DATA_DIR / record.filename
        if not config_file.is_file():
            continue
        record.content_hash = hashlib.sha256(config_file.read_bytes()).hexdigest()
        updated.append(record)

    if updated:
        ProgramConfigImport.objects.bulk_update(updated, ["content_hash"])
        print(f"✓ Backfilled content_hash for {len(updated)} program config import record(s)")


def clear_content_hashes(apps, schema_editor):
    ProgramConfigImport = apps.get_model("programs", "ProgramConfigImport")
    ProgramConfigImport.objects.update(content_hash="")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0165_add_nc_homeless_and_health_care_urgent_need_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="programconfigimport",
            name="content_hash",
            field=models.CharField(
                blank=True,
                default="",
                help_text="SHA-256 of the config file when it was applied. A file whose hash no longer "
                "matches is treated as pending again, so edits to a config are picked up on the next run.",
                max_length=64,
            ),
        ),
        migrations.RunPython(backfill_content_hashes, clear_content_hashes),
    ]
