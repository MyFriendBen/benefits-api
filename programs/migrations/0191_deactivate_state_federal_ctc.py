from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# The federal Child Tax Credit moves to one `federal_ctc` row on the `federal` white label,
# which every white label sees. These are the per-state copies it replaces, switched off
# rather than deleted so their ProgramSnapshot history survives. Each state's own child
# credit (`coctc`, `il_ctc`, `ma_cfc`) is a separate program and stays on, so rows are
# matched by (white label, name), never by `base_program`.
STATE_FEDERAL_CTC_ROWS = (
    ("co", "ctc"),
    ("co_tax_calculator", "ctc"),
    ("il", "ctc"),
    ("ma", "ctc"),
    ("nc", "ctc"),
    ("ks", "ks_ctc"),
    ("mo", "mo_ctc"),
    ("tx", "tx_ctc"),
    ("wa", "wa_ctc"),
)


def deactivate(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    Program = apps.get_model("programs", "Program")
    for white_label_code, name_abbreviated in STATE_FEDERAL_CTC_ROWS:
        white_label = WhiteLabel.objects.filter(code=white_label_code).first()
        if white_label is None:
            continue
        Program.objects.filter(white_label=white_label, name_abbreviated=name_abbreviated).update(active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0190_add_denver_public_schools_referrer"),
    ]

    operations = [
        # No reverse: switching these back on after `federal_ctc` is imported would show the
        # credit twice, their calculators no longer exist, and some were off before this ran.
        migrations.RunPython(deactivate, migrations.RunPython.noop),
    ]
