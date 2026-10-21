from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# The federal Child and Dependent Care Credit moves to one `federal_cdcc` row on the `federal`
# white label, which every white label sees. These are the per-state copies it replaces,
# switched off rather than deleted so their ProgramSnapshot history survives. Kansas's own
# credit (`ks_cdcc`) is a separate program and stays on.
STATE_FEDERAL_CDCC_ROWS = (
    ("ks", "ks_cdcc_federal"),
    ("mo", "mo_cdcc_federal"),
)


def deactivate(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    Program = apps.get_model("programs", "Program")
    for white_label_code, name_abbreviated in STATE_FEDERAL_CDCC_ROWS:
        white_label = WhiteLabel.objects.filter(code=white_label_code).first()
        if white_label is None:
            continue
        Program.objects.filter(white_label=white_label, name_abbreviated=name_abbreviated).update(active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0190_add_denver_public_schools_referrer"),
    ]

    operations = [
        # No reverse: switching these back on after `federal_cdcc` is imported would show the
        # credit twice, and their calculators no longer exist. Roll back by reverting the deploy.
        migrations.RunPython(deactivate, migrations.RunPython.noop),
    ]
