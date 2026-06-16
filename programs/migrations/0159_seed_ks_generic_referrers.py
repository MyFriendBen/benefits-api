from django.db import migrations


# Standard generic "how did you hear about us" referral options that belong on
# every white label, mirroring the generic set already present on existing WLs
# (e.g. wa). Partner-org referrers are added separately via the Django admin.
KS_GENERIC_REFERRERS = {
    "flyers": "Flyer",
    "friend": "Friend / Family / Word of Mouth",
    "other": "Other",
    "searchEngine": "Google or other search engine",
    "socialMedia": "Social Media",
    "testOrProspect": "Test / Prospective Partner",
}


def seed_ks_generic_referrers(apps, schema_editor):
    """Create the standard generic Referrer rows for the Kansas (ks) white label.

    Idempotent: skips any (white_label, referrer_code) that already exists so it
    never clobbers operational data. No-ops if the ks WhiteLabel does not exist
    yet (it is created as part of the KS launch); rerun after the WL exists, or
    add rows via the Django admin per the white label README.
    """
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection

    white_label = WhiteLabel.objects.filter(code="ks").first()
    if white_label is None:
        return

    for code, name in KS_GENERIC_REFERRERS.items():
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO programs_referrer
                    (white_label_id, referrer_code, name, show_in_dropdown,
                     is_partner, webhook_url)
                VALUES (%s, %s, %s, %s, %s, NULL)
                ON CONFLICT (white_label_id, referrer_code) DO NOTHING
                """,
                [white_label.id, code, name, True, False],
            )


def reverse_seed(apps, schema_editor):
    """No-op reverse — don't delete Referrer rows that may have operational
    (webhook/navigator) config attached."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0158_program_program_name_abbreviated_lowercase"),
    ]

    operations = [
        migrations.RunPython(seed_ks_generic_referrers, reverse_seed),
    ]
