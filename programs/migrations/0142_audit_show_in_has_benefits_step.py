from django.db import migrations
from django.db.models import Q

# Programs that should appear on the has-benefits step as selectable tiles.
# Includes both programs with calculators and tracking-only programs (has_calculator=False)
# that are used as categorical/presumptive eligibility inputs.
# show_in_has_benefits_step=True means the user can declare they already have it.
#
# Note: il_chp is intentionally excluded — IL CHP+ is captured via
# member.insurance.chp (per-member insurance questions), not screen-level.
PROGRAMS_TO_FLAG = [
    # CO
    ("co", "co_snap"),
    ("co", "co_tanf"),
    ("co", "co_wic"),
    ("co", "andcs"),
    ("co", "leap"),
    ("co", "ssi"),
    ("co", "ssdi"),
    ("co", "oap"),
    ("co", "cccap"),
    ("co", "cowap"),
    ("co", "rtdlive"),
    ("co", "co_section_8"),
    ("co", "co_andso"),
    ("co", "co_care"),
    # IL
    ("il", "il_snap"),
    ("il", "il_tanf"),
    ("il", "il_wic"),
    ("il", "ssi"),
    ("il", "ssdi"),
    ("il", "il_liheap"),
    ("il", "il_ccap"),
    # MA
    ("ma", "ma_snap"),
    ("ma", "ma_wic"),
    ("ma", "ssi"),
    ("ma", "ssdi"),
    ("ma", "ma_heap"),
    ("ma", "ma_section_8"),
    # NC
    ("nc", "nc_snap"),
    ("nc", "nc_tanf"),
    ("nc", "nc_wic"),
    ("nc", "ssi"),
    ("nc", "ssdi"),
    ("nc", "nc_aca"),
    ("nc", "nc_leap"),
    ("nc", "nc_cccap"),
    # TX
    ("tx", "tx_snap"),
    ("tx", "tx_tanf"),
    ("tx", "tx_wic"),
    ("tx", "tx_ssi"),
    ("tx", "tx_ssdi"),
    # CESN
    ("cesn", "cesn_snap"),
    ("cesn", "cesn_tanf"),
    ("cesn", "cesn_wic"),
    ("cesn", "cesn_ssi"),
    ("cesn", "cesn_ssdi"),
    ("cesn", "cesn_oap"),
    ("cesn", "cesn_section_8"),
    ("cesn", "cesn_rtdlive"),
    ("cesn", "cesn_andso"),
    ("cesn", "cesn_care"),
]


def _programs_q():
    q = Q()
    for wl_code, name_abbreviated in PROGRAMS_TO_FLAG:
        q |= Q(white_label__code=wl_code, name_abbreviated=name_abbreviated)
    return q


def forward(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(_programs_q()).update(show_in_has_benefits_step=True, active=True)
    # Reset anything not in the explicit list — PROGRAMS_TO_FLAG is the authoritative source.
    Program.objects.exclude(_programs_q()).update(show_in_has_benefits_step=False)


def reverse(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(_programs_q()).update(show_in_has_benefits_step=False)


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0141_create_gap_tracking_programs"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
