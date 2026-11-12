from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

# 2-1-1 New Jersey links to the NJ screener at /nj/step-1?referrer=211nj.
# add_config only writes the referrer_data blob, so the partner row that gives
# analytics a display name (and puts the partner in the dashboard's Partner
# filter) is created here.
#
# Hidden from the referral-source menu until launch: listing it now would show
# every NJ user a partner that is not live yet. The referral-options endpoint
# still returns hidden rows, so a ?referrer=211nj link skips the referral step.
# Flip show_in_dropdown in the Django admin at launch.
WHITE_LABEL_CODE = "nj"
REFERRER_CODE = "211nj"
NAME = "2-1-1 New Jersey"


def add_referrer(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    white_label = WhiteLabel.objects.filter(code=WHITE_LABEL_CODE).order_by("id").first()
    # A database without the NJ white label (a fresh test DB, or an environment that
    # never ran the state migrations) has nothing to attach the row to.
    if white_label is None:
        return

    # Raw SQL and DO NOTHING for the same reasons as 0183 and 0187: the historical
    # model has no _parler_meta, and an existing row may carry admin edits.
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
        ("programs", "0207_consolidate_shared_urgent_need_types"),
        ("screener", "0168_household_rows_default_id_ordering"),
    ]

    # No-op reverse, as in 0183 and 0187: don't delete a partner row that may have
    # picked up webhook/navigator/remove_programs config in the admin since, or that
    # screens already carry.
    operations = [migrations.RunPython(add_referrer, migrations.RunPython.noop)]
