from django.db import migrations

# (display name, two-letter state code) for every state-based white label.
# cesn is Colorado Energy Savings Navigator — a distinct code, but Colorado-based.
# _default and co_tax_calculator are intentionally excluded — not tied to a
# single real-world state.
STATE_WHITE_LABELS = {
    "co": ("Colorado", "CO"),
    "il": ("Illinois", "IL"),
    "wa": ("Washington", "WA"),
    "tx": ("Texas", "TX"),
    "ma": ("Massachusetts", "MA"),
    "nc": ("North Carolina", "NC"),
    "ks": ("Kansas", "KS"),
    "mo": ("Missouri", "MO"),
    "cesn": ("Colorado Energy Savings Navigator", "CO"),
}

# Standard "how did you hear about us" options every white label should have.
GENERIC_REFERRERS = {
    "flyers": "Flyer",
    "friend": "Friend / Family / Word of Mouth",
    "merit": "Merit America",
    "other": "Other",
    "searchEngine": "Google or other search engine",
    "socialMedia": "Social Media",
    "testOrProspect": "Test / Prospective Partner",
}


def create_state_white_labels(apps, schema_editor):
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection

    for code, (name, state_code) in STATE_WHITE_LABELS.items():
        # code has no unique constraint at the DB level (screener/models.py),
        # and bulk_import creates WhiteLabel rows via bare .objects.create()
        # in several places, so a drifted database could have duplicates —
        # get_or_create's .get() would raise MultipleObjectsReturned and fail
        # the deploy. Since this migration exists specifically to repair
        # drifted databases, don't assume the column is clean: match the same
        # defensive read configuration/views.py:46 already uses.
        white_label = WhiteLabel.objects.filter(code=code).order_by("id").first()
        if white_label is None:
            white_label = WhiteLabel.objects.create(name=name, code=code, state_code=state_code, feature_flags={})

        # A pre-existing row (however it was created) may be missing
        # state_code (e.g. created earlier by bulk_import, which never sets
        # it) — backfill it explicitly in that case.
        if not white_label.state_code:
            white_label.state_code = state_code
            white_label.save()

        # Seed generic referrer codes. Raw SQL, not the ORM: apps.get_model()
        # returns a frozen historical model that parler never registers
        # _parler_meta on, so Referrer.objects.create() raises
        # AttributeError: 'NoneType'.get_all_fields() (see 0141/0145/0159/0164).
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

        # merit may already exist as a Referrer row classified as a partner
        # (is_partner=True) by 0145_seed_referrer_rows_from_referral_options.py.
        # ON CONFLICT DO NOTHING above won't touch that existing row, so
        # correct it explicitly now that it's confirmed generic.
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE programs_referrer SET is_partner = FALSE
                WHERE white_label_id = %s AND referrer_code = 'merit' AND is_partner = TRUE
                """,
                [white_label.id],
            )


def reverse_create(apps, schema_editor):
    # No-op: these rows may have since picked up real Program/Screen/other
    # operational data pointing at them, so deleting them isn't a safe rollback.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0175_ks_lieap_on_has_benefits_step"),
        ("screener", "0164_householdmember_was_in_foster_care"),
    ]

    operations = [
        migrations.RunPython(create_state_white_labels, reverse_create),
    ]
