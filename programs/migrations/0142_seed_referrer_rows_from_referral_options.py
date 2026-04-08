import json

from django.db import migrations


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
    Uses update_or_create to avoid conflicting with existing Referrer rows
    (which may already have webhook_url, webhook_functions, etc. configured).
    """
    Configuration = apps.get_model("configuration", "Configuration")
    Referrer = apps.get_model("programs", "Referrer")

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
            Referrer.objects.update_or_create(
                white_label=white_label,
                referrer_code=code,
                defaults={
                    "name": display_name,
                    "show_in_dropdown": True,
                },
            )

    # Note: we keep the referral_options Configuration rows in the DB as a
    # safe rollback path. They are no longer read by the frontend or API.


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
    ]
