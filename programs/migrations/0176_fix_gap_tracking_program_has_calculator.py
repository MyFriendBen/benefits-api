from django.db import migrations

# The white-label-scoped tracking-only programs from
# 0141_create_gap_tracking_programs.py. That migration only sets
# has_calculator=False on its create-new-row branch; for any of these that
# already existed under the same name (from a legacy DB snapshot, in our
# case), it reused the row as-is and left has_calculator at the model's
# default (True). No calculator class exists for any of these — they're
# meant to be has_benefit()-only tracking rows — so leaving has_calculator
# True causes the eligibility loop to crash with a KeyError on
# name_abbreviated when it reaches one.
GAP_TRACKING_PROGRAMS = [
    ("co", "co_andso"),
    ("co", "co_section_8"),
    ("ma", "ma_section_8"),
    ("co", "co_care"),
]


def fix_has_calculator(apps, schema_editor):
    Program = apps.get_model("programs", "Program")

    for white_label_code, name_abbreviated in GAP_TRACKING_PROGRAMS:
        Program.objects.filter(
            white_label__code=white_label_code,
            name_abbreviated=name_abbreviated,
            has_calculator=True,
        ).update(has_calculator=False)


def reverse_fix(apps, schema_editor):
    # No-op: has_calculator=True is the incorrect state we're fixing, so
    # reversing to it isn't a meaningful rollback.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0175_backfill_generic_referrers"),
    ]

    operations = [
        migrations.RunPython(fix_has_calculator, reverse_fix),
    ]
