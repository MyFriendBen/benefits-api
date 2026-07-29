from django.db import migrations

# CU Denver referrer overlay (MFB-1317). CU Denver reaches the screener via the
# `?referrer=cudenver` link on the CO white label, so this Referrer row is NOT a
# "how did you hear about us" dropdown option (show_in_dropdown=False). It is a
# named partner (is_partner=True) so it resolves to a display name in analytics
# (the `partner` column / mart_referrer_codes) rather than falling back to
# "Other". The overlay itself works without this row (the eligibility lookup is
# guarded), but the CU Denver dashboard (MFB-1568) needs it for the label.


def seed_cudenver_referrer(apps, schema_editor):
    """Create the CU Denver Referrer row on the CO white label.

    Idempotent: skips if (white_label, referrer_code) already exists. No-ops if
    the CO WhiteLabel does not exist yet.
    """
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection

    white_label = WhiteLabel.objects.filter(code="co").first()
    if white_label is None:
        return

    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO programs_referrer
                (white_label_id, referrer_code, name, show_in_dropdown,
                 is_partner, webhook_url)
            VALUES (%s, %s, %s, %s, %s, NULL)
            ON CONFLICT (white_label_id, referrer_code) DO NOTHING
            """,
            [white_label.id, "cudenver", "CU Denver", False, True],
        )


def reverse_seed(apps, schema_editor):
    """No-op reverse — don't delete a Referrer row that may have operational
    (webhook/navigator) config attached (matches 0159)."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0162_alter_program_base_program"),
    ]

    operations = [
        migrations.RunPython(seed_cudenver_referrer, reverse_seed),
    ]
