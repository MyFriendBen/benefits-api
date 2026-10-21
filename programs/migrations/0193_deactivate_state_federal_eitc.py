from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# The federal EITC moves to one `federal_eitc` row on the `federal` white label, which every
# white label sees. These are the per-state copies it replaces, switched off rather than
# deleted so their ProgramSnapshot history survives. Each state's own EITC (`coeitc`,
# `co_expanded_eitc`, `il_eitc`, `ma_maeitc`, `ks_eitc`) is a separate program and stays on.
STATE_FEDERAL_EITC_ROWS = (
    ("co", "eitc"),
    ("co_tax_calculator", "eitc"),
    ("il", "eitc"),
    ("ma", "eitc"),
    ("nc", "eitc"),
    ("ks", "ks_eitc_federal"),
    ("mo", "mo_eitc"),
    ("tx", "tx_eitc"),
    ("wa", "wa_eitc"),
)


def deactivate(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Program = apps.get_model("programs", "Program")
    for white_label_code, name_abbreviated in STATE_FEDERAL_EITC_ROWS:
        Program.objects.filter(white_label__code=white_label_code, name_abbreviated=name_abbreviated).update(
            active=False
        )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0192_add_year_type_to_program"),
    ]

    operations = [
        # No reverse: switching these back on after `federal_eitc` is imported would show EITC
        # twice, and some may have been off before this ran. Roll back in the admin.
        migrations.RunPython(deactivate, migrations.RunPython.noop),
    ]
