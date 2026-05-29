# Renames the Colorado Expanded EITC Program's name_abbreviated from
# "coeitc" to "co_expanded_eitc" so it no longer collides with the
# standard Colorado EITC Program (also name_abbreviated="coeitc"). The
# two are genuinely different benefits with different target populations
# (SSN holders vs ITIN filers) — see MFB-999.
#
# Match strategy: identify the row by (white_label.code, external_name)
# rather than primary key, because IDs differ between prod, staging, and
# local seed data. external_name="coexeitc" is the only stable identifier
# that distinguishes id 25 (Expanded EITC) from id 9 (standard CO EITC,
# external_name="coeitc").
#
# Calculator dispatch impact: Program.eligibility dispatches to a
# ProgramCalculator by name_abbreviated, and the existing
# co_tax_unit_calculators dict (programs/programs/co/pe/__init__.py)
# is updated in the same PR to map both "coeitc" and "co_expanded_eitc"
# to the same Coeitc class. Both programs produce identical PolicyEngine
# eligibility output today; MFB-1093 will replace the alias with a real
# CoExpandedEitc calculator that gates on the under-25-childless filer
# population.

from django.db import migrations


def forward(apps, schema_editor):
    # WhiteLabel lives in the screener app (re-exported from programs.models
    # for convenience). Importing directly avoids needing screener as an
    # explicit migration dependency for a read-only `code` lookup.
    from programs.models import WhiteLabel

    Program = apps.get_model("programs", "Program")

    try:
        co = WhiteLabel.objects.get(code="co")
    except WhiteLabel.DoesNotExist:
        return

    Program.objects.filter(
        white_label=co,
        external_name="coexeitc",
        name_abbreviated="coeitc",
    ).update(name_abbreviated="co_expanded_eitc")


def reverse(apps, schema_editor):
    from programs.models import WhiteLabel

    Program = apps.get_model("programs", "Program")

    try:
        co = WhiteLabel.objects.get(code="co")
    except WhiteLabel.DoesNotExist:
        return

    Program.objects.filter(
        white_label=co,
        external_name="coexeitc",
        name_abbreviated="co_expanded_eitc",
    ).update(name_abbreviated="coeitc")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0153_delete_dev_calculator_programs"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
