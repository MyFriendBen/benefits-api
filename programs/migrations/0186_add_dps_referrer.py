from django.db import migrations

# Denver Public Schools links to the CO screener at /co?referrer=dps.
# add_config only writes the referrer_data blob, so the partner row that gives
# analytics a display name is created here. Hidden from the referral-source
# menu: DPS users arrive by link, so the overlay already attributes them.
WHITE_LABEL_CODE = "co"
REFERRER_CODE = "dps"
NAME = "Denver Public Schools"


def add_referrer(apps, schema_editor):
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    white_label = WhiteLabel.objects.filter(code=WHITE_LABEL_CODE).order_by("id").first()
    if white_label is None:
        return

    # Raw SQL and DO NOTHING for the same reasons as 0181: the historical model
    # has no _parler_meta, and an existing row may carry admin edits.
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


def remove_referrer(apps, schema_editor):
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    white_label = WhiteLabel.objects.filter(code=WHITE_LABEL_CODE).order_by("id").first()
    if white_label is None:
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM programs_referrer WHERE white_label_id = %s AND referrer_code = %s",
            [white_label.id, REFERRER_CODE],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0185_create_federal_white_label"),
        ("screener", "0168_household_rows_default_id_ordering"),
    ]

    operations = [migrations.RunPython(add_referrer, remove_referrer)]
