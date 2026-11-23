from django.db import migrations

# The 2-1-1 organisations that belong in the referral-source menu but have no
# Referrer row. United Way of Greater Kansas City already has one in both
# states -- its 2-1-1 spans the state line, which is also why the `uwgkc`
# referrer code is configured identically in ks.py and mo.py.
#
# Names follow the prefix the existing UWGKC row established ("211 - United Way
# Greater Kansas City") but spell each organisation out. The partner has been
# asked to confirm the exact strings; correcting a name later is an admin edit,
# so shipping our best reading beats leaving the menu incomplete.
NEW_REFERRERS = {
    "ks": ("uwplains", "211 - United Way of the Plains"),
    "mo": ("uwgsl", "211 - United Way of Greater St. Louis"),
}


def add_referrers(apps, schema_editor):
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection

    for code, (referrer_code, name) in NEW_REFERRERS.items():
        # Defensive read, matching 0176: the column has held duplicates, so take
        # the oldest rather than assuming .get() is safe.
        white_label = WhiteLabel.objects.filter(code=code).order_by("id").first()
        if white_label is None:
            # A database without this white label (a fresh test DB, or an
            # environment that never ran the state migrations) has nothing to
            # attach the row to. Skipping is correct: add_config and the state
            # migrations own creating the white label itself.
            continue

        # Raw SQL, not the ORM: apps.get_model() returns a frozen historical
        # model that parler never registers _parler_meta on, so
        # Referrer.objects.create() raises AttributeError on
        # 'NoneType'.get_all_fields(). Same reason as 0141/0145/0159/0164/0176.
        #
        # DO NOTHING rather than an upsert: Referrer is unique on
        # (white_label_id, referrer_code), and a row that already exists may
        # carry an admin-edited name or flags that this migration has no
        # business overwriting.
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO programs_referrer
                    (white_label_id, referrer_code, name, show_in_dropdown,
                     is_partner, webhook_url)
                VALUES (%s, %s, %s, %s, %s, NULL)
                ON CONFLICT (white_label_id, referrer_code) DO NOTHING
                """,
                [white_label.id, referrer_code, name, True, True],
            )


def remove_referrers(apps, schema_editor):
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection

    for code, (referrer_code, _name) in NEW_REFERRERS.items():
        white_label = WhiteLabel.objects.filter(code=code).order_by("id").first()
        if white_label is None:
            continue

        # Screen.referrer_code is a CharField, not a foreign key, so removing a
        # Referrer leaves existing screens' attribution strings intact.
        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM programs_referrer WHERE white_label_id = %s AND referrer_code = %s",
                [white_label.id, referrer_code],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0180_ssi_msp_csfp_current_edition"),
        ("screener", "0089_whitelabel_cms_method"),
    ]

    operations = [migrations.RunPython(add_referrers, remove_referrers)]
