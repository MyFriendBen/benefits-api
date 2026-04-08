import json

from django.db import migrations, models


def extract_display_name(value):
    """Extract display name from referral option value.

    Values are either a plain string ("2-1-1 Colorado") or a dict
    with _label and _default_message keys.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and "_default_message" in value:
        return value["_default_message"]
    return ""


def seed_referrer_rows(apps, schema_editor):
    """Create Referrer rows from existing referral_options Configuration data.

    For each WL's referral_options config, create a Referrer row per option.
    Uses raw SQL to avoid django-parler incompatibility with historical models
    in migrations. Skips codes that already have a Referrer row (e.g. existing
    webhook/navigator config) to avoid overwriting operational data.
    """
    Configuration = apps.get_model("configuration", "Configuration")
    db = schema_editor.connection

    referral_configs = Configuration.objects.filter(name="referral_options", active=True)

    for config in referral_configs:
        white_label = config.white_label
        options = config.data or {}

        # Configuration.data is stored via OrderedJSONField which double-encodes
        # values as JSON strings. Handle both the double-encoded (str) and
        # properly-decoded (dict) cases.
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except (json.JSONDecodeError, ValueError):
                options = {}

        for code, value in options.items():
            display_name = extract_display_name(value)
            with db.cursor() as cursor:
                # Insert if no row exists for this (white_label, referrer_code).
                # If a row already exists (e.g. has webhook config), update only
                # name and show_in_dropdown to avoid clobbering other fields.
                cursor.execute(
                    """
                    INSERT INTO programs_referrer
                        (white_label_id, referrer_code, name, show_in_dropdown,
                         webhook_url)
                    VALUES (%s, %s, %s, %s, NULL)
                    ON CONFLICT (white_label_id, referrer_code)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        show_in_dropdown = EXCLUDED.show_in_dropdown
                    """,
                    [white_label.id, code, display_name, True],
                )

    # Note: we keep the referral_options Configuration rows in the DB as a
    # safe rollback path. They are no longer read by the frontend or API.

    # Back-fill name for any existing Referrer rows that have a blank name,
    # using referrer_code as the fallback so the NOT NULL / non-blank
    # constraint added below can be applied cleanly.
    with db.cursor() as cursor:
        cursor.execute("UPDATE programs_referrer SET name = referrer_code WHERE name = ''")


def reverse_seed(apps, schema_editor):
    """No-op reverse — we don't want to delete Referrer rows that may have
    webhook/navigator config attached."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0141_add_referrer_name_dropdown_and_per_wl_uniqueness"),
        ("configuration", "0005_alter_configuration_white_label"),
    ]

    operations = [
        migrations.RunPython(seed_referrer_rows, reverse_seed),
        migrations.AlterField(
            model_name="referrer",
            name="name",
            field=models.CharField(max_length=255),
        ),
        migrations.AddConstraint(
            model_name="referrer",
            constraint=models.CheckConstraint(
                check=~models.Q(name=""),
                name="referrer_name_not_blank",
            ),
        ),
    ]
