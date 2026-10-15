from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# 2-1-1 Kansas and 2-1-1 Missouri now refer statewide under their own codes,
# replacing United Way of Greater Kansas City's `uwgkc`. The names are
# provisional until the partner confirms them; correcting one later is an
# admin edit.
NEW_REFERRERS = {
    "ks": ("211ks", "2-1-1 Kansas"),
    "mo": ("211mo", "2-1-1 Missouri"),
}

# Retired from the referral-source menu but never deleted: the dashboards name a
# screen's partner by joining Screen.referrer_code to this table, so a deleted
# row would turn every screen already attributed to it into "Other". The
# referral-options endpoint still returns hidden rows, so an old
# ?referrer=uwgkc link keeps skipping the referral step.
HIDDEN_REFERRERS = {
    "ks": ("uwgkc", "uwplains"),
    "mo": ("uwgkc", "uwgsl"),
}


def _white_label_id(apps: Apps, code: str) -> int | None:
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    # Defensive read, matching 0176/0181: the column has held duplicates, so
    # take the oldest rather than assuming .get() is safe.
    white_label = WhiteLabel.objects.filter(code=code).order_by("id").first()
    # A database without this white label (a fresh test DB, or an environment
    # that never ran the state migrations) has nothing to attach rows to.
    return white_label.id if white_label is not None else None


def switch_referrers(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    db = schema_editor.connection

    for code, (referrer_code, name) in NEW_REFERRERS.items():
        white_label_id = _white_label_id(apps, code)
        if white_label_id is None:
            continue

        # Raw SQL, not the ORM: apps.get_model() returns a frozen historical
        # model that parler never registers _parler_meta on. Same reason as
        # 0181/0183. DO NOTHING rather than an upsert, so a row that already
        # exists keeps any admin-edited name or flags.
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO programs_referrer
                    (white_label_id, referrer_code, name, show_in_dropdown,
                     is_partner, webhook_url)
                VALUES (%s, %s, %s, %s, %s, NULL)
                ON CONFLICT (white_label_id, referrer_code) DO NOTHING
                """,
                [white_label_id, referrer_code, name, True, True],
            )

    _set_dropdown_visibility(apps, schema_editor, visible=False)


def restore_referrers(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    db = schema_editor.connection

    _set_dropdown_visibility(apps, schema_editor, visible=True)

    for code, (referrer_code, _name) in NEW_REFERRERS.items():
        white_label_id = _white_label_id(apps, code)
        if white_label_id is None:
            continue

        # Keep a row any screen already carries: the dashboards name a screen's
        # partner from it, the same reason the retired codes are hidden rather
        # than deleted.
        with db.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM programs_referrer r
                WHERE r.white_label_id = %s AND r.referrer_code = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM screener_screen s
                      WHERE s.white_label_id = r.white_label_id
                        AND s.referrer_code = r.referrer_code
                  )
                """,
                [white_label_id, referrer_code],
            )


def _set_dropdown_visibility(apps: Apps, schema_editor: BaseDatabaseSchemaEditor, visible: bool) -> None:
    db = schema_editor.connection

    # Every white label with the code, not just the oldest: the referral-options
    # endpoint reads referrers across all of them, so a retired code left
    # visible on a duplicate would stay in the menu.
    for code, referrer_codes in HIDDEN_REFERRERS.items():
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE programs_referrer SET show_in_dropdown = %s
                WHERE referrer_code = ANY(%s)
                  AND white_label_id IN (SELECT id FROM screener_whitelabel WHERE code = %s)
                """,
                [visible, list(referrer_codes), code],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0186_rename_nc_nslp"),
    ]

    operations = [migrations.RunPython(switch_referrers, restore_referrers)]
