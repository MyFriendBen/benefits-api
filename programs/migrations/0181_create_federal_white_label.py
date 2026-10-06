from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

# Federal programs live under this white label and are shown to every other white label
# (programs/federal.py). It has no state, no configuration module and no referrers: no
# screen is ever created under it, so it only needs the row for `Program.white_label`.
FEDERAL_CODE = "federal"
FEDERAL_NAME = "Federal Programs"


def create_federal_white_label(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    # `code` has no unique constraint, so read defensively like 0176 does rather than
    # get_or_create, which raises on a duplicated code.
    if not WhiteLabel.objects.filter(code=FEDERAL_CODE).exists():
        WhiteLabel.objects.create(code=FEDERAL_CODE, name=FEDERAL_NAME, state_code=None, feature_flags={})


def reverse_create(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    # No-op: programs may point at the row by the time anyone rolls back.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0180_ssi_msp_csfp_current_edition"),
        ("screener", "0168_household_rows_default_id_ordering"),
    ]

    operations = [
        migrations.RunPython(create_federal_white_label, reverse_create),
    ]
