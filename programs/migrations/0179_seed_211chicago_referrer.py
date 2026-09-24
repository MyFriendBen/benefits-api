from django.db import migrations

REFERRER_CODE = "211chicago"
REFERRER_NAME = "211 Metro Chicago"


def seed_211chicago_referrer(apps, schema_editor):
    """Create the 211 Metro Chicago Referrer row on the Illinois white label.

    is_partner=True is what puts the partner in the Metabase Partner filter and
    groups them as a partner (rather than a generic option) in the screener's
    referral-source dropdown.

    show_in_dropdown=False because they have not launched: listing them as a
    "how did you hear about us" option would show every Illinois user a partner
    that is not live yet. Flip it in the Django admin at launch — which is also
    the point at which the dashboard predicate should move from referrer_code to
    the partner display name, so dropdown-attributed screens are not dropped.

    Idempotent: skips the row if (white_label, referrer_code) already exists, so
    it never clobbers webhook or navigator config added through the admin.
    """
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection

    white_label = WhiteLabel.objects.filter(code="il").first()
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
            [white_label.id, REFERRER_CODE, REFERRER_NAME, False, True],
        )


def reverse_seed(apps, schema_editor):
    """No-op reverse — don't delete a Referrer row that may have picked up
    operational (webhook/navigator/remove_programs) config since."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0178_ma_ccdf_year_2026"),
    ]

    operations = [
        migrations.RunPython(seed_211chicago_referrer, reverse_seed),
    ]
