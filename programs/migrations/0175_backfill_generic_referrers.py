from django.db import migrations

# Standard "how did you hear about us" options every white label should have.
# Based on GENERIC_REFERRER_CODES in 0145_seed_referrer_rows_from_referral_options.py,
# which only seeded white labels that existed at the time it ran (white labels
# created afterward — il, tx, wa, ks, mo — never got these rows), plus "merit":
# 0145 treated it as a named partner (is_partner=True) despite a comment there
# calling it "intentionally generic", and configuration/white_labels/README.md
# has always listed it as a standard generic code. Confirmed with the team
# that Merit America should be generic — included here as such.
GENERIC_REFERRERS = {
    "flyers": "Flyer",
    "friend": "Friend / Family / Word of Mouth",
    "merit": "Merit America",
    "other": "Other",
    "searchEngine": "Google or other search engine",
    "socialMedia": "Social Media",
    "testOrProspect": "Test / Prospective Partner",
}


def backfill_generic_referrers(apps, schema_editor):
    # Raw SQL, not the ORM: apps.get_model() returns a frozen historical model
    # that parler never registers _parler_meta on, so Referrer.objects.create()
    # raises AttributeError: 'NoneType'.get_all_fields() (see 0141/0145/0159/0164,
    # which hit the same issue and use the same workaround).
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection

    for wl in WhiteLabel.objects.exclude(code="[PLACEHOLDER]"):
        for code, name in GENERIC_REFERRERS.items():
            with db.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO programs_referrer
                        (white_label_id, referrer_code, name, show_in_dropdown,
                         is_partner, webhook_url)
                    VALUES (%s, %s, %s, %s, %s, NULL)
                    ON CONFLICT (white_label_id, referrer_code) DO NOTHING
                    """,
                    [wl.id, code, name, True, False],
                )

    # merit may already exist as a Referrer row from
    # 0145_seed_referrer_rows_from_referral_options.py, which classified it as
    # a partner (is_partner=True) for any white label that already had it in
    # referral_options config. ON CONFLICT DO NOTHING above wouldn't touch
    # that existing row, so correct its classification explicitly now that
    # it's confirmed generic.
    with db.cursor() as cursor:
        cursor.execute("UPDATE programs_referrer SET is_partner = FALSE WHERE referrer_code = 'merit' AND is_partner = TRUE")


def reverse_backfill(apps, schema_editor):
    # No-op, same reasoning as 0145_seed_referrer_rows_from_referral_options.py:
    # rows created here may since have picked up webhook/navigator config that
    # a rollback shouldn't destroy.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0174_consolidate_missed_program_categories"),
    ]

    operations = [
        migrations.RunPython(backfill_generic_referrers, reverse_backfill),
    ]
