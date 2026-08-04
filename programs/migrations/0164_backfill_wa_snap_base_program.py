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
    # Historical model, not the live one: this has to keep running from scratch after a
    # future model change (0163 dropping Program.value_type is the precedent). Traversing
    # the FK by `white_label__code` sidesteps the live/historical WhiteLabel mismatch that
    # 0152 / 0154 worked around by using live models throughout.
    Program = apps.get_model("programs", "Program")

    Program.objects.filter(white_label__code="wa", name_abbreviated="wa_snap", base_program__isnull=True).update(
        base_program="snap"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0163_drop_program_value_type"),
    ]

    operations = [
        # No-op reverse: forward fills NULLs only and doesn't record which rows it filled,
        # so clearing every wa_snap row on the way back would also discard a base_program
        # set independently (import_program_config writes the same field).
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
