# Sets base_program="snap" on WA's SNAP program (name_abbreviated="wa_snap"), the only
# SNAP variant across the 8 white labels with a NULL base_program.
#
# Why it matters: the same PR switches the dead `has_benefit("snap")` reads to
# `has_base_benefit("snap")`. has_base_benefit() resolves through base_program, so
# without this row WA would be the one state where reported SNAP receipt still fails to
# confer categorical/adjunctive eligibility (WA Head Start, WA WIC) — verified against
# real screens: a wa_snap recipient returned has_benefit("snap")=False AND
# has_base_benefit("snap")=False, only has_benefit("wa_snap")=True.
#
# Match strategy follows 0154_rename_coexeitc_name_abbreviated: identify by
# (white_label.code, name_abbreviated) rather than primary key, because IDs differ
# between prod, staging, and local seed data. Guarded so it's a no-op where the WA white
# label or program doesn't exist (e.g. a fresh test database).

from django.db import migrations


def forward(apps, schema_editor):
    # Live models, per the pattern in 0154 / 0152: a historical Program's FK expects a
    # historical WhiteLabel, so mixing the two raises ValueError.
    from programs.models import Program, WhiteLabel

    try:
        wa = WhiteLabel.objects.get(code="wa")
    except WhiteLabel.DoesNotExist:
        return

    Program.objects.filter(white_label=wa, name_abbreviated="wa_snap", base_program__isnull=True).update(
        base_program="snap"
    )


def reverse(apps, schema_editor):
    from programs.models import Program, WhiteLabel

    try:
        wa = WhiteLabel.objects.get(code="wa")
    except WhiteLabel.DoesNotExist:
        return

    Program.objects.filter(white_label=wa, name_abbreviated="wa_snap", base_program="snap").update(base_program=None)


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0162_alter_program_base_program"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
