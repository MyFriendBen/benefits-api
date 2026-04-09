from django.db import migrations
from django.db.models import Q

# All programs that should appear on the current benefits step.
# Includes both programs used as categorical/presumptive eligibility inputs in calculators
# and tracking-only programs (has_calculator=False) created in 0137/0141.
# Both show_in_has_benefits_step and active must be True to appear on the step.
PROGRAMS_TO_FLAG = [
    # CO
    ("co", "co_snap"),
    ("co", "co_tanf"),
    ("co", "co_wic"),
    ("co", "andcs"),
    ("co", "leap"),
    ("co", "ssi"),
    ("co", "ssdi"),
    ("co", "chp"),
    ("co", "oap"),
    ("co", "cccap"),
    ("co", "cowap"),
    ("co", "rtdlive"),
    ("co", "section_8"),
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
    ("il", "il_chp"),
    # MA
    ("ma", "ma_snap"),
    ("ma", "ma_wic"),
    ("ma", "ssi"),
    ("ma", "ssdi"),
    ("ma", "ma_heap"),
    ("ma", "section_8"),
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
    ("cesn", "cesn_chp"),
    ("cesn", "cesn_oap"),
    ("cesn", "cesn_section_8"),
    ("cesn", "cesn_rtdlive"),
    ("cesn", "cesn_andso"),
    ("cesn", "cesn_care"),
    ("cesn", "cesn_medicaid"),
]


def _programs_q():
    q = Q()
    for wl_code, name_abbreviated in PROGRAMS_TO_FLAG:
        q |= Q(white_label__code=wl_code, name_abbreviated=name_abbreviated)
    return q


def forward(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(_programs_q()).update(show_in_has_benefits_step=True, active=True)


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
