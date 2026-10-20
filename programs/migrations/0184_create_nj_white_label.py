from django.db import migrations

# Standard "how did you hear about us" options every white label should have.
# Kept identical to 0176_create_state_white_labels.py's GENERIC_REFERRERS.
GENERIC_REFERRERS = {
    "flyers": "Flyer",
    "friend": "Friend / Family / Word of Mouth",
    "merit": "Merit America",
    "other": "Other",
    "searchEngine": "Google or other search engine",
    "socialMedia": "Social Media",
    "testOrProspect": "Test / Prospective Partner",
}

CODE = "nj"
NAME = "New Jersey"
STATE_CODE = "NJ"


def create_nj_white_label(apps, schema_editor):
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection
    # Keep every ORM call on the database this migration is running against
    # (matters for `migrate --database=<alias>`).
    manager = WhiteLabel.objects.using(db.alias)

    # code has no unique constraint at the DB level (screener/models.py), and
    # bulk_import creates WhiteLabel rows via bare .objects.create() in several
    # places, so a drifted database could have duplicates — get_or_create's
    # .get() would raise MultipleObjectsReturned and fail the deploy. Match the
    # same defensive read configuration/views.py:46 and 0176 already use.
    white_label = manager.filter(code=CODE).order_by("id").first()
    if white_label is None:
        white_label = manager.create(
            name=NAME, code=CODE, state_code=STATE_CODE, feature_flags={}, cms_method="nj_hubspot"
        )

    if not white_label.state_code:
        white_label.state_code = STATE_CODE
        white_label.save(using=db.alias)

    if not white_label.cms_method:
        white_label.cms_method = "nj_hubspot"
        white_label.save(using=db.alias)

    # Seed generic referrer codes. Raw SQL, not the ORM: apps.get_model()
    # returns a frozen historical model that parler never registers
    # _parler_meta on, so Referrer.objects.create() raises
    # AttributeError: 'NoneType'.get_all_fields() (see 0141/0145/0159/0164/0176).
    for referrer_code, referrer_name in GENERIC_REFERRERS.items():
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO programs_referrer
                    (white_label_id, referrer_code, name, show_in_dropdown,
                     is_partner, webhook_url)
                VALUES (%s, %s, %s, %s, %s, NULL)
                ON CONFLICT (white_label_id, referrer_code) DO NOTHING
                """,
                [white_label.id, referrer_code, referrer_name, True, False],
            )


def reverse_create(apps, schema_editor):
    # No-op: this row may have since picked up real Program/Screen/other
    # operational data pointing at it, so deleting it isn't a safe rollback.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0183_seed_211chicago_referrer"),
    ]

    operations = [
        migrations.RunPython(create_nj_white_label, reverse_create),
    ]
