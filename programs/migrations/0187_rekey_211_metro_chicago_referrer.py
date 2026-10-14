from django.db import migrations

LIVE_CODE = "211_metro_chicago"
SEEDED_CODE = "211chicago"
NAME = "211 Metro Chicago"


def _il_id(apps) -> int | None:
    white_label = apps.get_model("screener", "WhiteLabel").objects.filter(code="il").first()
    return white_label.id if white_label else None


def rekey_211_metro_chicago(apps, schema_editor) -> None:
    """Move the 211 Metro Chicago overlay onto the referrer code they already use.

    Prod has carried an admin-made `211_metro_chicago` row since before 0183 seeded
    `211chicago`, and their live link uses it. il.py's referrer_data is now keyed to
    `211_metro_chicago`, so:

    1. Make sure that row exists everywhere (staging and local never had it), with
       prod's values. ON CONFLICT DO NOTHING leaves prod's row exactly as the admin
       set it.
    2. Delete the `211chicago` row 0183 seeded, but only while it carries no
       webhook, navigators or removed programs, so admin config added since is never
       dropped. Screen.referrer_code is plain text, so no screen references the row.

    Raw SQL, as in 0183: parler never registers _parler_meta on historical models,
    so Referrer.objects.create() fails inside a migration.
    """
    white_label_id = _il_id(apps)
    if white_label_id is None:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO programs_referrer
                (white_label_id, referrer_code, name, show_in_dropdown, is_partner, webhook_url)
            VALUES (%s, %s, %s, TRUE, TRUE, NULL)
            ON CONFLICT (white_label_id, referrer_code) DO NOTHING
            """,
            [white_label_id, LIVE_CODE, NAME],
        )
        cursor.execute(
            """
            DELETE FROM programs_referrer r
            WHERE r.white_label_id = %s
              AND r.referrer_code = %s
              AND COALESCE(r.webhook_url, '') = ''
              AND NOT EXISTS (SELECT 1 FROM programs_referrer_webhook_functions x WHERE x.referrer_id = r.id)
              AND NOT EXISTS (SELECT 1 FROM programs_referrer_primary_navigators x WHERE x.referrer_id = r.id)
              AND NOT EXISTS (SELECT 1 FROM programs_referrer_remove_programs x WHERE x.referrer_id = r.id)
            """,
            [white_label_id, SEEDED_CODE],
        )


def restore_seeded_referrer(apps, schema_editor) -> None:
    """Put back 0183's hidden `211chicago` row. `211_metro_chicago` stays: in prod it
    predates this migration, so reversing must not delete it."""
    white_label_id = _il_id(apps)
    if white_label_id is None:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO programs_referrer
                (white_label_id, referrer_code, name, show_in_dropdown, is_partner, webhook_url)
            VALUES (%s, %s, %s, FALSE, TRUE, NULL)
            ON CONFLICT (white_label_id, referrer_code) DO NOTHING
            """,
            [white_label_id, SEEDED_CODE, NAME],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0186_rename_nc_nslp"),
    ]

    operations = [
        migrations.RunPython(rekey_211_metro_chicago, restore_seeded_referrer),
    ]
