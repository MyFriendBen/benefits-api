# Deletes the two Program rows that referenced the now-removed
# programs/programs/dev/ calculators:
#
#   - CO _dev_ineligible (external_name=_dev_ineligible) — the actual dev
#     "always ineligible" stub.
#   - CO _dev_ineligible (external_name=leap_seasonal) — a real-looking
#     program parked on the dev-ineligible calculator as a placeholder.
#     Audit on 2026-05-29 confirmed zero code references to leap_seasonal
#     across benefits-api, benefits-calculator, data-queries, and
#     integrations, and zero rows in screener_current_benefits.
#
# Both rows were active=false in prod, so this deletion does not change
# any user-facing eligibility output. Together with the removal of
# programs/programs/dev/ in the same PR, this eliminates one of the two
# (white_label, name_abbreviated) collisions blocking the upcoming
# UniqueConstraint (MFB-999).
#
# Match strategy: identify rows by (white_label.code, name_abbreviated,
# external_name) rather than primary key, because IDs differ between
# prod, staging, and local seed data.

from django.db import migrations

# (white_label_code, name_abbreviated, external_name) for each row to delete.
ROWS_TO_DELETE = [
    ("co", "_dev_ineligible", "_dev_ineligible"),
    ("co", "_dev_ineligible", "leap_seasonal"),
]


def forward(apps, schema_editor) -> None:
    # Use live models throughout (mirrors the pattern established in
    # 0152_backfill_has_benefits_categories). Mixing live WhiteLabel with
    # a historical Program from apps.get_model causes
    # `ValueError: Cannot query "Colorado": Must be "WhiteLabel" instance.`
    # because the historical Program's FK expects a historical WhiteLabel.
    from programs.models import Program, WhiteLabel

    wl_by_code = {wl.code: wl for wl in WhiteLabel.objects.all()}

    for wl_code, name_abbreviated, external_name in ROWS_TO_DELETE:
        wl = wl_by_code.get(wl_code)
        if wl is None:
            continue
        Program.objects.filter(
            white_label=wl,
            name_abbreviated=name_abbreviated,
            external_name=external_name,
        ).delete()


def reverse(apps, schema_editor) -> None:
    # Intentional no-op: these rows referenced calculators that no longer
    # exist (programs/programs/dev/ was removed in the same PR). Recreating
    # them on reverse would re-introduce the (white_label, name_abbreviated)
    # collision this PR fixes, and any eligibility lookup against them
    # would crash on the missing calculator. A separate migration can
    # re-seed dev programs if dev calculators ever come back.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0152_backfill_has_benefits_categories"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
