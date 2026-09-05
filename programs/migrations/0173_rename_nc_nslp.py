# Renames North Carolina's National School Lunch Program row's name_abbreviated
# from the bare federal key "nslp" to "nc_nslp" so it dispatches to the new
# NcNslp calculator (programs/programs/cross_white_label/nslp/nc.py) instead of
# the bare federal SchoolLunch calculator.
#
# Root cause (MFB-1683): SchoolLunch sends no state code, so PolicyEngine defaults
# to universal-free-meals behavior and every NC household over the reduced-price
# cutoff is shown as FREE. NcNslp adds NcStateCodeDependency, matching the
# il_nslp / ks_nslp / mo_nslp / tx_nslp / wa_nslp precedent.
#
# Match strategy: filter by (white_label=nc, name_abbreviated="nslp"). Unlike the
# coeitc rename (0154), NC has only one nslp-family row per white label, so no
# additional external_name disambiguation is needed.

from django.db import migrations


def forward(apps, schema_editor):
    from programs.models import Program, WhiteLabel

    try:
        nc = WhiteLabel.objects.get(code="nc")
    except WhiteLabel.DoesNotExist:
        return

    Program.objects.filter(white_label=nc, name_abbreviated="nslp").update(name_abbreviated="nc_nslp")


def reverse(apps, schema_editor):
    from programs.models import Program, WhiteLabel

    try:
        nc = WhiteLabel.objects.get(code="nc")
    except WhiteLabel.DoesNotExist:
        return

    Program.objects.filter(white_label=nc, name_abbreviated="nc_nslp").update(name_abbreviated="nslp")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0172_consolidate_shared_program_categories"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
