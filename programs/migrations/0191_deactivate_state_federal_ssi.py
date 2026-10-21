from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# Federal SSI is one `federal_ssi` row on the `federal` white label, which every white label
# sees. These are the per-state copies it replaces, switched off rather than deleted so their
# ProgramSnapshot history survives. The State supplements (`ma_ssp`, `andcs`, `ks_sspp`, ...)
# are separate programs and stay on.
STATE_SSI_ROWS = (
    ("co", "ssi"),
    ("il", "ssi"),
    ("ma", "ssi"),
    ("nc", "ssi"),
    ("cesn", "cesn_ssi"),
    ("ks", "ks_ssi"),
    ("mo", "mo_ssi"),
    ("tx", "tx_ssi"),
    ("wa", "wa_ssi"),
)


def deactivate(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Program = apps.get_model("programs", "Program")
    for white_label_code, name_abbreviated in STATE_SSI_ROWS:
        # `update` is a no-op for a row that is missing or already inactive.
        Program.objects.filter(white_label__code=white_label_code, name_abbreviated=name_abbreviated).update(
            active=False
        )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0190_add_denver_public_schools_referrer"),
    ]

    operations = [
        # No reverse: the calculators behind these rows no longer exist, so switching them
        # back on would fail the results page for that white label. Roll back by reverting
        # the deploy.
        migrations.RunPython(deactivate, migrations.RunPython.noop),
    ]
