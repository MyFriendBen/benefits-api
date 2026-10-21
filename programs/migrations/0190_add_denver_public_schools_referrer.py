from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

# The link partners actually received is /co/step-1?referrer=denver-public-schools,
# so co.py's DPS branding is now keyed to that code and this adds its partner row.
# 0187's `dps` row stays: the dashboards name a screen's partner by joining
# Screen.referrer_code/referral_source to this table, and a screen already
# carries `dps`.
WHITE_LABEL_CODE = "co"
REFERRER_CODE = "denver-public-schools"
NAME = "Denver Public Schools"


def add_referrer(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    white_label = WhiteLabel.objects.filter(code=WHITE_LABEL_CODE).order_by("id").first()
    if white_label is None:
        return

    # Raw SQL and DO NOTHING for the same reasons as 0187: the historical model
    # has no _parler_meta, and prod's row is made in the admin before this deploys.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO programs_referrer
                (white_label_id, referrer_code, name, show_in_dropdown,
                 is_partner, webhook_url)
            VALUES (%s, %s, %s, %s, %s, NULL)
            ON CONFLICT (white_label_id, referrer_code) DO NOTHING
            """,
            [white_label.id, REFERRER_CODE, NAME, False, True],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0189_add_211ks_211mo_referrers"),
        ("screener", "0168_household_rows_default_id_ordering"),
    ]

    # No-op reverse, as in 0187: the row may be admin-made or carry admin config.
    operations = [migrations.RunPython(add_referrer, migrations.RunPython.noop)]
